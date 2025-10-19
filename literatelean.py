import sys
import re

lean_lines = []
bib_contents = ""

# the contents are always a triple (typ, int, str) with the following meaning:
#   * typ is always int 0 or int 1, 0 means that str is tex and 1 means it's lean
#   * int is the corresponding line number in the lean file (meaningful only when typ = 1)
#   * str is the content
tex_lines = []

labels = {}

STATE_LEAN = 0
STATE_TEX = 1
STATE_BIB = 2

state = STATE_LEAN

if len(sys.argv) != 3:
  print("USAGE: %s <file> <base_url>" % sys.argv[0])
  exit(-1)

BASE_URL = sys.argv[2]

for line in open(sys.argv[1]).readlines():
  clean_line = line.strip()
  if clean_line == "/-@":
    state = STATE_TEX
  elif clean_line == "@-/":
    state = STATE_LEAN
  elif clean_line == "/-!":
    state = STATE_BIB
  elif clean_line == "!-/":
    state = STATE_LEAN
  else:
    if state == STATE_TEX:
      def escape(match):
        ident = match.group(1)
        return "\\hyperref[lean:%s]{\\ttfamily %s}" % (ident, ident.replace('_', '\\_'))
      line = re.sub(r'\\lean{([^}]+)}', escape, line)
      tex_lines.append((0,0,line))
    elif state == STATE_BIB:
      bib_contents += line
    elif state == STATE_LEAN:
      lean_lines.append(line)
      if line[:-1].endswith("; "):
        indentation = (len(line) - len(line.lstrip())) * ' '
        if len(tex_lines) > 0 and not tex_lines[-1][2].strip() == '-- ...':
          tex_lines.append((1, len(lean_lines), indentation + '-- ...\n'))
      else:
        tokens = clean_line.split()
        if len(tokens) > 0 and tokens[0] in ["def", "theorem", "inductive", "class"]:
          ident = tokens[1].split(":")[0]
          line = line[:-1] + ("!\\phantomsection\\label{lean:%s}!\n" % ident)
        tex_lines.append((1,len(lean_lines),line))

tex_lines.append((0,0,"")) # this helps

def remove_useless_tex_lines():
  i = 0
  while i < len(tex_lines):
    (typ, leanlineno, line) = tex_lines[i]
    # remove the first empty lines from every lstlisting:
    if typ == 1 and len(line.strip()) == 0 and (i == 0 or tex_lines[i-1][0] == 0):
      del tex_lines[i]
      continue
    # remove the last empty lines from every lstlisting:
    if typ == 0 and i > 0 and tex_lines[i-1][0] == 1 and len(tex_lines[i-1][2].strip()) == 0:
      del tex_lines[i-1]
      continue
    i += 1

def process_tex_lines():
  out = ""
  i = 0
  last_lean_start_line = 0
  while i < len(tex_lines):
    (typ, leanlineno, line) = tex_lines[i]
    if i > 0 and typ == 1 and tex_lines[i-1][0] == 0:
      last_lean_start_line = leanlineno
      out += """\\noindent\\begin{tikzpicture}
  \\node[anchor=north west, inner sep=0] (code) at (0,0) {
    \\begin{minipage}{\\linewidth}
      \\begin{minted}[escapeinside=!!,fontsize=\\small,baselinestretch=0.85,bgcolor=codebg]{lean4}\n"""
    if i > 0 and typ == 0 and tex_lines[i-1][0] == 1:
      out += """\\end{minted}
    \\end{minipage}
  };
  \\node[anchor=north east, yshift=-5pt] at (code.north east) {
    \\href{%s#L%d-%d}{\includegraphics[width=2em]{git.png}}
  };
\\end{tikzpicture}
""" % (BASE_URL, last_lean_start_line, tex_lines[i-1][1])
    out += line
    i += 1
  return out

remove_useless_tex_lines()

open("out.tex", "w").write(process_tex_lines())
open("out.lean", "w").write("".join(lean_lines))
open("out.bib", "w").write(bib_contents)
