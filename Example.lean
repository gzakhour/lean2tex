/-@tex

\title{A Simple Utility for Literate Lean}
\author{George Zakhour}
\date{\today}
\maketitle

\section{Introduction}

The \texttt{literatelean.py} Python 3 program reads a literate lean file and produces three files:

\begin{enumerate}
  \item \texttt{out.tex}: a \LaTeX~file meant to be compiled with \texttt{xelatex} and the accompanying \texttt{report.tex} files,
  \item \texttt{out.lean}: a Lean file with all the literate text stripped away,
  \item \texttt{out.bib}: a bibliography file containing the citations of the literate lean file.
\end{enumerate}

This very document is compiled from the literate lean file \texttt{Example.lean}.

\section{Simple Literate Lean}

A literate lean file must be first and foremost a legal Lean file~\cite{moura2021lean} that the lean compiler and checker approve of.

The text and its accompanying citations in the \LaTeX~file are always inside comments.

\subsection{Human Readable Text}

The human readable part of the document must be valid \LaTeX, but it may not be a complete document.
To the user's convenience we supplied a minimal \texttt{report.tex} \LaTeX~document and \texttt{Makefile} that may help you in getting started.

All text must appear between the comment delimeters: \texttt{/-@tex} and \texttt{@-/}, or more convienently between \texttt{/-@} and \texttt{@-/}.
Each delimeter must appear on its own line with no text before or after it (whitespace is allowed).

Multiple human readable blocks are allowed in a document.
The final \LaTeX~document will concatenate all these blocks in the same order that they appear in.

\subsection{Bibliography}

Bibliography data must be valid bibtex~\cite{patashnik1984bibtex}.
Like human readable text, these must appear inside comments and their delimeters are \texttt{/-@bib} and \texttt{@-/}.
Only whitespace may appear around these delimeters on the line they occupy.

/-@bib
@article{patashnik1984bibtex,
  title={BIBTEX 101},
  author={Patashnik, Oren},
  journal={TUGboat},
  volume={15},
  pages={269--273},
  year={1984}
}
@inproceedings{moura2021lean,
  title={The lean 4 theorem prover and programming language},
  author={Moura, Leonardo de and Ullrich, Sebastian},
  booktitle={International Conference on Automated Deduction},
  pages={625--635},
  year={2021},
  organization={Springer}
}
@-/

Just like human readable text, many bibliography blocks are allowed and the resulting bib file will be the concatenation of all the blocks.

Human-readable text and bibliography commenst may be arbitrarily nested.

\subsection{Lean Text}

As a literate lean program is a Lean program then Lean code does not appear inside comments.

By default every line of Lean code makes it in the \LaTeX~document inside a formated \texttt{minted} block.
It is possible to hide parts of Lean code by wrapping them inside \texttt{-- \{\{\{} and \texttt{-- \}\}\}}.
All the lean lines in between two comments will not be displayed and instead a \texttt{-- ...} will be displayed instead exactly where the opening delimiter is.

Lean comments are equally moved into the \LaTeX~output.
That choice was made to encourage moving all comments into a literate format.
It may be interesting to look into single line comments annotating some Lean code to be added as footnotes.

The \texttt{minted} block will always have a git logo in its top left that, when clicked, redirects to the relevant lines in the resulting stripped \texttt{out.lean} file.

For example, these three lines of Lean code start by evaluating the identity function to 1,
then they check the type of the result of applying the identity function to 2, and finally
checks the type of the identity function.

@-/

#eval  (λ x ↦ x) 1
#check (λ x ↦ x) 2
#check (λ x ↦ x)

/-@tex

Sadly, this utility is too simple to use the Lean LSP to show the result of the \texttt{\#eval} and \texttt{\#check} calls.

Or even to show errors in a nicely formatted way.

But it does have a cool feature that allows you to reference definitions, theorems, inductive types, and type classes from the \LaTeX~code.
This can be done using the \texttt{{\textbackslash}lean} macro which the utility expands before passing it to the \LaTeX~compiler.

For example, \lean{nat} is the definition of the Peano~\cite{kennedy2012peano} numbers.

@-/

-- Peano Numbers
inductive nat where
  | zero
  | succ (n: nat)

/-@tex

The definition of addition, in \lean{add}, is the following:

@-/

def add (n m: nat) : nat := match n with
  | .zero => m
  | .succ n' => nat.succ (add n' m)

/-@

And the proof that add is commutative, \lean{add_comm}, is the following.
We omit the proof at the base case as it's obvious.
If you wish to see it you may do so by clicking on the git icon

@-/

theorem add_comm: ∀ (n m : nat), add n m = add m n := by
  intros n; induction n
  case zero => -- {{{
    intros m; induction m;
    case zero => simp only [add];
    case succ m' ih => simp only [add, ←ih]; -- }}}
  case succ n ih =>
    intros m; induction m
    case zero => simp only [add, ih]
    case succ m' ih' => simp [add,ih,←ih']

/-@tex

The tool is again simple, it creates a label to definitions, theorems, inductive types, and type
classes if and only if the declaration starts on a new line with the keyword \texttt{def},
\texttt{theorem}, \texttt{inductive}, and \texttt{class} keyword (respectively) being the first
token of the line and the identifier to be bound is the second token.


\subsection{Index}

An index is automatically collected of all the definitions, theorems, inductive types, and type classes.
If you wish to have them rendered in the final document you must have the two commands \texttt{{\textbackslash}makeindex} and \texttt{{\textbackslash}printindex}.

For example, in the following code, without even referring to the Printable type class in the text through the \texttt{{\textbackslash}lean} macro, the symbol still makes it to the index.

@-/

class Printable (α: Type) where
  print: α → String

instance : Printable nat where
  print n := toString n
    where toString (n: nat) : String :=
      match n with
      | nat.zero => "0"
      | nat.succ n => "S" ++ toString n

instance : Printable String where
  print x := x

#eval Printable.print (nat.succ (nat.succ nat.zero))
#eval Printable.print "Hello, World!"

/-@bib
@book{kennedy2012peano,
  title={Peano: life and works of Giuseppe Peano},
  author={Kennedy, Hubert},
  volume={4},
  year={2012},
  publisher={Springer Science \& Business Media}
}
@-/
