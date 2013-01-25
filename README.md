springerbot
===========

Requirements: PyPDF2, socksipy

* Downloads book chapters from link.springer.com and merges them.
* Fetches metadata and creates a BibTeX entry.
* SOCKS proxy support.
* Inserts a document outline (booksmarks/index/toc.) for chapters into the pdf file.

You need a download permission for springerlink, many university networks have one.
If you have SSH access, you can create a SOCKS proxy (ssh -D ...) and use it
for downloading.
