LEAN_FILE=Example.lean
BASE_URL=https://github.com/geezee/lean2tex/blob/main/example/out.lean

example.pdf: example.tex out.bib out.lean out.tex proof_out.tex
	xelatex -shell-escape example.tex
	bibtex example
	xelatex -shell-escape example.tex
	xelatex -shell-escape example.tex

proof_out.tex out.bib out.lean out.tex: ../lean2tex.py $(LEAN_FILE)
	python3 ../lean2tex.py $(LEAN_FILE) $(BASE_URL)
