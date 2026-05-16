DECK    := deck.md
OUTDIR  := output
PLANTUML := java -jar ~/tools/plantuml-snapshot.jar
DIAGRAMS := $(wildcard diagrams/*.puml)

.PHONY: all diagrams html pdf pptx clean

all: diagrams html

## Generate PNG charts from PlantUML source files
diagrams: $(DIAGRAMS)
	mkdir -p diagrams
	$(PLANTUML) diagrams/*.puml -o ../diagrams/

## Render HTML (fast — use for preview and presenting)
html: $(DECK)
	mkdir -p $(OUTDIR)
	marp $(DECK) -o $(OUTDIR)/sprint-review.html

## Render PDF (for archiving and sharing)
pdf: $(DECK)
	mkdir -p $(OUTDIR)
	marp $(DECK) --pdf -o $(OUTDIR)/sprint-review.pdf

## Render PowerPoint (for stakeholders who need .pptx)
pptx: $(DECK)
	mkdir -p $(OUTDIR)
	marp $(DECK) --pptx -o $(OUTDIR)/sprint-review.pptx

clean:
	rm -rf $(OUTDIR)

## Prerequisites check
check:
	@command -v marp    || echo "MISSING: npm install -g @marp-team/marp-cli"
	@command -v java    || echo "MISSING: Java runtime (for PlantUML)"
	@test -f ~/tools/plantuml-snapshot.jar || echo "MISSING: plantuml-snapshot.jar not found at ~/tools/"
