class BugCounter:
    """Class to count the number of bugs in bugs.md file and update the number
    of bugs, confirmed and fixed bugs in the file.
    """

    def __init__(self):
        self.num_bugs = 0
        self.num_confirmed = 0
        self.num_fixed = 0
        self.num_by_bugs = 0
        self.num_by_confirmed = 0
        self.num_by_fixed = 0
        self.by_flag = False

    def read_file(self, path: str) -> list[str]:
        """Read the file and return the data as a list of strings."""
        with open(path, "r", encoding="utf-8") as f:
            data = f.readlines()
        return data

    def write_data(self, data: list, path: str):
        """Write the data to the file."""
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(data)

    def update_number(self):
        """Update the number of bugs, confirmed and fixed bugs in the file."""
        data = self.read_file("./bugs.md")
        for line in data:
            if "# Byproduct bugs" in line:
                self.by_flag = True
            if not self.by_flag:
                self.num_bugs += line.count("](")
                self.num_confirmed += line.count("confirmed")
                self.num_fixed += line.count("fixed")
            else:
                self.num_by_bugs += line.count("](")
                self.num_by_confirmed += line.count("confirmed")
                self.num_by_fixed += line.count("fixed")

        self.num_confirmed += self.num_fixed
        self.num_by_confirmed += self.num_by_fixed
        if not data[2].startswith("(Byproduct bugs included)"):
            raise RuntimeError(
                "The first line of bugs.md should start with '(Byproduct bugs included)'"
            )
        data[2] = (
            "(Byproduct bugs included) "
            f"Total bugs: **{self.num_bugs + self.num_by_bugs}**, "
            f"confirmed: **{self.num_confirmed + self.num_by_confirmed}**, "
            f"Fixed: **{self.num_fixed + self.num_by_fixed}**.<br/>\n"
        )
        data[4] = (
            f"(Byproduct bugs excluded) "
            f"Total bugs: **{self.num_bugs}**, "
            f"confirmed: **{self.num_confirmed}**, "
            f"Fixed: **{self.num_fixed}**.<br/>\n"
        )
        self.write_data(data, "./bugs.md")


if __name__ == "__main__":
    bug_counter = BugCounter()
    bug_counter.update_number()
