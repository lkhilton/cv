# Quarto Academic CV


- [Setup this repository](#setup-this-repository)
- [Setup Zotero](#setup-zotero)
- [Customize your CV](#customize-your-cv)
- [Rendering](#rendering)
- [Further customization](#further-customization)

## Setup this repository

1.  Fork this repository from GitHub and clone it to your computer.
    Clear out the contents of the `references` folder.
2.  Install the `multibib` Quarto extension. This enables you to have
    more than one set of references in different parts of your CV.
    `quarto add pandoc-ext/multibib`
3.  Run this locally (not on a remote server). Use a recent version of R
    (currently set up for R 4.5.1) and update your tlmgr installation.
4.  Install R packages with `renv::init()` and choose to restore from
    the lock file.

## Setup Zotero

1.  Install Zotero and install the Better BibTeX plugin.
2.  Retrieve your publications from the internet with the Zotero browser
    plugin. For talks and posters, you can usually find them in
    supplemental issues for journals affiliated with each conference
    (e.g. *Blood* for ASH, *Hematological Oncology* for ICML). You can
    manually add citations for talks and posters that do not appear in a
    journal.
3.  When you add a talk or a poster, change the “Item Type” to
    “Conference Paper.” This will remove the Journal field, and you can
    add the name of the conference to both the “Proceedings Title” and
    “Conference Name” fields. Add the city and state/country to the
    “Place” field.
4.  Organize your items into collections for each type of
    paper/presentation. Mine includes:
    - Published articles and preprints
    - Oral presentations at conferences
    - Poster presentations
    - Invited/non-peer-reviewed contributions (i.e. commentary)
5.  Set up an automatic export in Zotero. Right-click any of your
    collections from step 4 and select Export. Make sure to check “Use
    Journal Abbreviation” and “Keep updated”. When prompted, write the
    exported .bib file to the `references` folder within your clone of
    this repository. Any time you add items to your CV collections, your
    `.bib` files will be automatically updated.

## Customize your CV

1.  Edit the yaml header in the `cv.qmd` file:
    - Replace the title with your own name and degree status.
    - Under the `bibliography` key, update the file paths to point to
      your various `.bib` files as exported during the Zotero setup
      steps.
2.  Place references at their appropriate divs throughout your CV. In
    the example below, `refs-papers` will insert the complete
    bibliography of items stored in the the `.bib` file under the
    `papers` key in the bibliography section of the yaml header.

<!-- -->

        ::: {#refs-papers}
        :::

1.  For other CV components, you can either type them in (see e.g. the
    **Service** section of the example CV), or you can include them in
    tables in the `components` directory. Update the paths to various
    `components` tsv files throughout. Quarto will automatically render
    the correct type of table for output to Word .docx, .pdf, or
    Github-flavored markdown .md files. If you include linebreaks in any
    of the contents of your tables, see examples in the **Appointments**
    and **Education** sections for how to achieve this.

## Rendering

`quarto render cv.qmd`

This command will generate all 3 formats documented in the yaml header.
The GitHub-flavored markdown output is written to README.md so that your
CV can be hosted on your fork of this repository.

## Further customization

Under the **Publications** header, there is some code to count the
number of first- or co-first authored papers. First-authored papers are
counted based on the CV-owner’s name appearing in the citation key
(e.g. `@article{hilton`). To obtain the number of co-first-authored
papers, you’ll need to manually edit the entries in the
`references/papers.bib` file to include an asterisk beside the names of
the co-first authors. The code then looks for the presence of the
`{*Hilton}` pattern and counts those items as first-authored
publications.

Unfortunately I could not identify a way to get my own name in bold
whenever it appears in the output, so currently you’ll have to
post-process the output .docx or .md files to achieve that.
