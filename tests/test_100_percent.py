"""Final tests to achieve 100% coverage."""

import pytest

from gaussian_lsp.parser.gjf_parser import GJFParser


class TestHundredPercentCoverage:
    """Tests specifically targeting uncovered branches."""

    def test_line_435_to_451_loop_completion(self):
        """Test line 435->451: for loop completes without finding ModRedundant.

        The loop at line 435 iterates to find non-empty lines after geometry.
        We need the loop to complete (not break early) so it can reach line 451.
        """
        parser = GJFParser()
        # Content with blank line at end - the for loop will iterate but lines[j]
        # will be empty/falsy at the end, causing the loop to exit without break
        content = """# B3LYP/6-31G(d)

Test

0 1
O  0.000000  0.000000  0.000000

"""
        job = parser.parse(content)
        assert len(job.atoms) == 1

    def test_line_484_to_489_title_already_set(self):
        """Test line 484->489: title is already set when in title section.

        This happens when we have multiple lines in the title section,
        but the first line already set the title.
        """
        parser = GJFParser()
        # This should trigger the case where title is already set
        content = """# B3LYP/6-31G(d)

First Line
Second Line

0 1
H 0.0 0.0 0.0
"""
        job = parser.parse(content)
        assert job.title == "First Line"
