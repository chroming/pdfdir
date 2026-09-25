"""Page-label policy for an exported PDF.

Page labels name physical pages in a reader; outlines still target page indexes.
"""

from dataclasses import dataclass
from typing import Optional

from pypdf.constants import PageLabelStyle
from pypdf.generic import NameObject


@dataclass(frozen=True)
class PageLabelPlan:
    mode: str = "preserve"
    body_start_page: Optional[int] = None  # One-based physical PDF page.

    def validate(self, page_count):
        if self.mode == "preserve":
            if self.body_start_page is not None:
                raise ValueError("Body start page requires Roman/body page labels")
            return
        if self.mode != "roman-body":
            raise ValueError("Unknown page-label mode: {}".format(self.mode))
        if not isinstance(self.body_start_page, int) or isinstance(
            self.body_start_page, bool
        ) or not 1 <= self.body_start_page <= page_count:
            raise ValueError(
                "Body start page must be between 1 and {}".format(page_count)
            )


def apply_page_labels(reader, writer, plan):
    """Copy existing labels or create Roman front matter and decimal body labels."""
    plan.validate(len(writer.pages))
    if plan.mode == "preserve":
        labels = reader.trailer["/Root"].get("/PageLabels")
        if labels is not None:
            # Clone the number tree into the destination writer. Keeping its raw
            # structure preserves prefixes, numbering styles and extra ranges.
            writer._root_object[NameObject("/PageLabels")] = labels.clone(writer)
        return

    first_body_index = plan.body_start_page - 1
    if first_body_index:
        writer.set_page_label(
            0, first_body_index - 1, style=PageLabelStyle.LOWERCASE_ROMAN, start=1
        )
    writer.set_page_label(
        first_body_index,
        len(writer.pages) - 1,
        style=PageLabelStyle.DECIMAL,
        start=1,
    )
