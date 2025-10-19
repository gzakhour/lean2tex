LEAN_FILE=Example.lean
BASE_URL=https://github.com/geezee/literatelean/blob/main/out.lean

report.pdf: report.tex out.bib out.lean out.tex
	xelatex -shell-escape report.tex
	bibtex report
	xelatex -shell-escape report.tex
	xelatex -shell-escape report.tex

out.bib: $(LEAN_FILE)
	python3 literatelean.py $(LEAN_FILE) $(BASE_URL)

out.lean: $(LEAN_FILE)
	python3 literatelean.py $(LEAN_FILE) $(BASE_URL)

out.tex: $(LEAN_FILE)
	python3 literatelean.py $(LEAN_FILE) $(BASE_URL)
