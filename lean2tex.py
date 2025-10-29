import sys
import re
from enum import Enum

import subprocess
import json
import threading
import os
import uuid
import time
import queue

class LeanLSP:

  def __init__(self):
    self.responses = {} # id -> json
    self.requests = set() # id
    self.stdout = queue.Queue()
    self.stderr = queue.Queue()
    self.diagnostics = {} # line nmuber -> str
    self.document_uri = ""
    self.all_symbols = None

    self.server = subprocess.Popen(
        ['lean', '--server'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    threading.Thread(target=self._process_buf, args=(self.server.stdout, self.stdout), daemon=True).start()
    threading.Thread(target=self._process_buf, args=(self.server.stderr, self.stderr), daemon=True).start()
    threading.Thread(target=self._process_queues, daemon=True).start()

    self.send("initialize", {
      "processId": os.getpid(),
      "rootUri": None,
      "capabilities": {},
    })
    self.send("initialized", {}, has_id=False)

  def _process_queues(self):
    while True:
      if not self.stderr.empty(): self.stderr.get()
      if not self.stdout.empty():
        header = b''
        while not header.endswith(b'\r\n\r\n'): header += self.stdout.get()
        content_length = int(header.split(b':')[1].strip())
        response = b''
        for _ in range(content_length): response += self.stdout.get()
        response = json.loads(response)
        if "id" in response: self.responses[response["id"]] = response
        if "method" in response and response["method"] == "textDocument/publishDiagnostics":
          for diagnostic in response["params"]["diagnostics"]:
            self.diagnostics[diagnostic["range"]["end"]["line"]] = diagnostic["message"]

  def _process_buf(self, buf, queue):
    while True: queue.put(buf.read(1))
    buf.close()

  def send(self, method, params=None, has_id=True):
    id = str(uuid.uuid4())
    payload = { "jsonrpc": "2.0", "method": method, "params": params, }
    if has_id: payload["id"] = id
    body = json.dumps(payload)
    content_length = len(body.encode('utf-8'))
    if has_id: self.requests.add(id)
    self.server.stdin.write(f'Content-Length: {content_length}\r\n\r\n{body}'.encode('utf-8'))
    self.server.stdin.flush()
    if has_id:
      while id not in self.responses: time.sleep(0.01)
      return self.responses[id]

  def stop(self):
    self.server.stdin.close()

  def load_file(self, filename):
    self.document_uri = "file://" + os.path.abspath("filename")
    self.send("textDocument/didOpen", {
      "textDocument": {
        "uri": self.document_uri,
        "languageId": "lean",
        "version": 1,
        "text": open(filename, "r").read()
      }
    }, has_id=False)

  def get_all_symbols_at_line(self, lineno):
    if self.all_symbols is None:
      response = self.send("textDocument/documentSymbol", {
        "textDocument": { "uri": self.document_uri, },
      })
      self.all_symbols = {}
      for symbol in response["result"]:
        line = symbol["range"]["start"]["line"]
        name = symbol["name"].strip()
        if line not in self.all_symbols: self.all_symbols[line] = []
        self.all_symbols[line].append(name)
    return self.all_symbols[lineno] if lineno in self.all_symbols else []

  def get_proof_state_at(self, line, char):
    proof = self.send("$/lean/plainGoal", {
      "textDocument": { "uri": self.document_uri, },
      "position": { "line": line, "character": char }
    })["result"]
    if proof is None or "goals" not in proof:
      return None
    return "\n\n".join(proof["goals"])

  def get_diagnostic(self, line):
    return self.diagnostics[line] if line in self.diagnostics else None



class State(Enum):
  LEAN = 0
  TEX = 1
  BIB = 2


class Processor:
  def handle(self, state, lineno, line): return
  def export(self, file): return


class BibProcessor(Processor):
  def __init__(self):
    self.contents = ""

  def handle(self, state, lineno, line):
    if state == State.BIB:
      self.contents += line

  def export(self, file):
    open(file, "w").write(self.contents)


class LeanProcessor(Processor):
  def __init__(self):
    self.contents = []

  def handle(self, state, lineno, line):
    if state == State.LEAN:
      self.contents.append(line)

  def export(self, file):
    open(file, "w").write("".join(self.contents))

  def getlineno(self):
    return len(self.contents)


class TeXProcessor(Processor):
  def __init__(self, git_url, lean_processor, lean_lsp):
    self.git_url = git_url
    self.lean_processor = lean_processor
    self.lean_lsp = lean_lsp

    self.lines = []
    self.proof_states = [] # (lineno, char, goal)

    self.previous_state = None
    self.hiding_lean = False
    self.hiding_lean_numlines = 0
    self.start_lean_lineno = 0
    self.previous_proof_state = None

  def handle(self, state, lineno, line):

    # ignore anything not meant for us
    if state != State.LEAN and state != State.TEX:
      return

    if self.previous_state is None:
      self.previous_state = state

    # When the state changes we either need to open minted or close it
    if self.previous_state != state:
      self.previous_state = state
      self.hiding_lean = False
      # we open minted OR we ignore new empty lines
      if state == State.LEAN:
        self.previous_proof_state = None
        self.start_lean_lineno = self.lean_processor.getlineno()
        self.lines.append("""
\\noindent\\begin{tikzpicture}
  \\node [anchor=north west, inner sep=0] (code) at (0,0) {
    \\begin{minipage}{\\linewidth}
      \\begin{minted}[escapeinside=!!,fontsize=\\footnotesize,baselinestretch=0.85,bgcolor=codebg]{lean4}\n
""")
      # we close minted
      elif state == State.TEX:
        # skip beginning lines that are empty
        while len(self.lean_processor.contents[self.start_lean_lineno].strip()) == 0:
          self.start_lean_lineno += 1
        # skip beginning lines that are empty
        last_line_no = self.lean_processor.getlineno() - 1
        while len(self.lean_processor.contents[last_line_no].strip()) == 0:
          last_line_no -= 1
        self.lines.append("""
      \\end{minted}
    \\end{minipage}
  };
  \\node [anchor=north east, yshift=-5pt] at (code.north east) {
    \\href{%s#L%d-L%d}{\\includegraphics[width=2em]{git.png}}
  };
\\end{tikzpicture}
""" % (self.git_url, self.start_lean_lineno+1, last_line_no+1))

    # Regardless of whether the state changes or not, now we need to handle each line

    # if we're processing LaTeX we need to expand \lean{def} command and sanitize underscores
    if state == State.TEX:
      line = re.sub(
        r'\\lean{([^}]+)}',
        lambda m: '\\leanRef{%s}{%s}' % (m.group(1).replace(' ', ''), m.group(1).replace('_', '\\_')),
        line)
      self.lines.append(line)
      return

    # if we're processing Lean we need to:
    #   1. hide everything between the comment delimeters
    #   2. add labels to symbols being defined on that current line
    #   3. add indicators and links to proof states wherever it changes
    elif state == State.LEAN:
      if not self.hiding_lean:
        if line.rstrip().endswith("-- {{"+"{"): # my vim don't jiggle jiggle, it folds
          self.hiding_lean_numlines = 0
          line = line.replace("-- {{"+"{","")
          self.hiding_lean = True
        line = line[:-1]
        (line, extras) = self._get_extra_proof_state_lines(line, lineno) # it's important that `line` has not been manipulated
        line = self._inject_goal_state(line, lineno)
        line = self._inject_def_symbol_labels(line, lineno)
        line += '\n'
        if len(line.strip()) == 0:
          self.lines.append(line)
        else:
          self.lines.append(self._render_lineno(self.lean_processor.getlineno()) + line)
        self.lines += extras
        self._inject_diagnostic_messages(line, lineno)
      elif line.rstrip().endswith("-- }}"+"}"):
        self.hiding_lean_numlines += 1
        self.lines.append(self._new_comment(line, "%d lines hidden\n" % self.hiding_lean_numlines))
        self.hiding_lean = False
      else:
        self.hiding_lean_numlines += 1
      return

  def _inject_def_symbol_labels(self, line, lineno):
    for symbol in self.lean_lsp.get_all_symbols_at_line(int(lineno)-1): # lsp is 0-indexed
      line += "!\\leanLabel{%s}{%s}!" % (symbol.replace(' ',''), symbol.replace('_', '\\_'))
    return line

  def _inject_goal_state(self, line, lineno):
    points = []
    for c in range(len(line)):
      if line[c].isspace(): continue
      goal = self.lean_lsp.get_proof_state_at(lineno-1, c) # lsp is 0-indexed
      if self.previous_proof_state != goal:
        self.previous_proof_state = goal
        if len(goal) == 0: continue # we do not log terminated proofs
        # lean has this awful feature of applying a tactic when the cursor's just after the first character
        # of the tactic name, so it's hard to find where the tactic actually ends. Next best thing is to add
        # the link at the next space.
        start = max(0, c-1)
        while c < len(line) and not line[c].isspace() and line[c] not in ['[',']',',',';']: c += 1
        self.proof_states.append((lineno, c, line[start:c], goal, self.lean_processor.getlineno()))
        points.append((start, c))

    new_line = ""
    for c in range(len(line)+1):
      if len(points) > 0:
        if points[0][1] == c:
          points.pop(0)
          new_line += "!\leanProofGoalRef{%d}{%d}!" % (lineno, c)
      if c < len(line): new_line += line[c]

    return new_line

  def _render_lineno(self, lineno, count=4, phantom=False):
    n = str(lineno)
    pad = "\\phantom{0}" * (count - len(n))
    if phantom:
      return "!\\phantom{\\tiny{" + pad + n + "}}! "
    else:
      return "!\\tiny{" + pad + n + "}! "

  def _new_comment(self, line, contents):
    indent = " " * (len(line) - len(line.lstrip()))
    lineno = self._render_lineno(self.lean_processor.getlineno(), phantom=True)
    nl = "\n" if len(line.strip()) == 0 or line[-1] != "\n" else ""
    return lineno + indent + "-- " + contents + nl

  def _get_extra_proof_state_lines(self, line, lineno):
    line = line.rstrip()
    match = re.match(r'^.*-- >>>(.*)$', line)
    if match is None: return (line, [])
    tokens = list(map(lambda t: t.strip(), match.group(1).split()))
    line = re.sub(r"-- >>>.*$", "", line)
    proof = self.lean_lsp.get_proof_state_at(lineno-1, len(line))
    if len(tokens) == 0:
      return (line, list(map(lambda x: self._new_comment(line, x),
                             self._format_proof_goal(proof).split("\n"))))
    else:
      proof_lines = proof.split('\n')
      extras = []
      for t in tokens:
        for pl in proof_lines:
          match = re.match('^' + t + '.*$', pl)
          if match is None: continue
          extras.append(self._new_comment(line, pl))
          break
      return (line, extras)

  def _inject_diagnostic_messages(self, line, lineno):
    diagnostic = self.lean_lsp.get_diagnostic(lineno-1) # lsp is 0-indexed
    if diagnostic is not None:
      self.lines.append(self._new_comment("", diagnostic.replace('\n', '\n--')))

  def _format_proof_goal(self, proofGoal):
    return proofGoal.replace('✝', '†')

  def export(self, file):
    open(file, "w").write("".join(self.lines))
    open("proof_" + file, "w").write("\section{Proof Goals}\n\n" + "\n\n".join([
      "\\begin{leanProofGoal}{%d}{%d}{%s}{%d}\n%s\n\\end{leanProofGoal} " % (lineno, char, name, lean_lineno, self._format_proof_goal(goal))
      for (lineno, char, name, goal, lean_lineno) in self.proof_states
    ]))


def main():
  if len(sys.argv) != 3:
    print("USAGE: %s <file> <base_url>" % sys.argv[0])
    exit(-1)

  lean_lsp = LeanLSP()
  lean_lsp.load_file(sys.argv[1])

  bib_processor = BibProcessor()
  lean_processor = LeanProcessor()
  tex_processor = TeXProcessor(sys.argv[2], lean_processor, lean_lsp)

  state_stack = [State.LEAN]
  lineno = 0

  all_lines = list(open(sys.argv[1]).readlines())
  num_lines = len(all_lines)

  for line in all_lines:
    lineno += 1
    print("Processing line %d/%d (%.2f%%)" % (lineno, num_lines, lineno*100/num_lines), end='\r')
    sys.stdout.flush()
    clean_line = line.strip()
    if clean_line == "/-@tex" or clean_line == "/-@":
      state_stack.append(State.TEX)
    elif clean_line == "@-/":
      state_stack.pop()
      state_lean_hiding = False
    elif clean_line == "/-@bib":
      state_stack.append(State.BIB)
    else:
      state = state_stack[-1]
      bib_processor.handle(state, lineno, line)
      lean_processor.handle(state, lineno, line) # NOTE this must happen before tex_processor
      tex_processor.handle(state, lineno, line)

  # Just in case the tex processor's last seen state is Lean, we give it an extra empty line
  # so it closes all the environment it needs to
  tex_processor.handle(State.TEX, lineno+1, "")

  bib_processor.export("out.bib")
  lean_processor.export("out.lean")
  tex_processor.export("out.tex")
  print()

if __name__ == '__main__':
  main()
