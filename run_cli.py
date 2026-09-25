import argparse

from src.pdfdirectory import add_directory
from src.pdf.page_labels import PageLabelPlan

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add content to PDF.")
    parser.add_argument("pdfPath", type=str, help="path of PDF")
    parser.add_argument("tocPath", type=str, help="path of contents file")
    parser.add_argument("--offset", type=int, default=0, help="Page offset of contents")
    parser.add_argument(
        "--page-labels", choices=("preserve", "roman-body"), default="preserve",
        help="Preserve source page labels, or number front matter i, ii... and body 1, 2...",
    )
    parser.add_argument(
        "--body-start-page", type=int, default=None,
        help="One-based physical PDF page where body page 1 starts; defaults to offset + 1",
    )
    parser.add_argument(
        "--l0",
        type=str,
        default=r"^\d+\.\s?",
        help="Regular expression of level 0 of content",
    )
    parser.add_argument(
        "--l1",
        type=str,
        default=r"^\d+\.\d+\w?\s?",
        help="Regular expression of level 1 of content",
    )
    parser.add_argument(
        "--l2",
        type=str,
        default=r"^\d+\.\d+\.\d+\w?\s?",
        help="Regular expression of level 2 of content",
    )
    parser.add_argument(
        "--l3",
        type=str,
        default=r"^\d+\.\d+\.\d+\.\d+\w?\s?",
        help="Regular expression of level 3 of content",
    )
    parser.add_argument(
        "--l4",
        type=str,
        default=r"^\d+\.\d+\.\d+\.\d+\.\d+\w?\s?",
        help="Regular expression of level 4 of content",
    )
    parser.add_argument(
        "--l5",
        type=str,
        default=r"^\d+\.\d+\.\d+\.\d+\.\d+\.\d+\w?\s?",
        help="Regular expression of level 5 of content",
    )
    args = parser.parse_args()

    pdfPath = args.pdfPath
    tocPath = args.tocPath
    offset = args.offset
    if args.page_labels == "preserve" and args.body_start_page is not None:
        parser.error("--body-start-page requires --page-labels roman-body")
    if args.page_labels == "roman-body":
        body_start = args.body_start_page if args.body_start_page is not None else offset + 1
        if body_start < 1:
            parser.error("body start page must be at least 1; pass --body-start-page")
        label_plan = PageLabelPlan("roman-body", body_start)
    else:
        label_plan = PageLabelPlan()

    # -- load toc
    f = open(tocPath)
    toc = f.read()
    f.close()
    add_directory(
        toc, offset, pdfPath, args.l0, args.l1, args.l2, args.l3, args.l4, args.l5,
        page_label_plan=label_plan,
    )
