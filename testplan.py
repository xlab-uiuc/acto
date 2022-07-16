
class TreeNode():

    def __init__(self) -> None:
        self.children = {}
        pass

    def add_child(self, key: str, child):
        self.children[key] = child

    def get_children(self) -> dict:
        return self.children

    def get_testcases(self):
        pass

    def add_testcases(self):
        pass

    def disable_node(self):
        pass

    def disable_subtree(self):
        pass

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.children['ITEM']
        else:
            return self.children[key]

class TestPlan():

    def __init__(self, root: TreeNode) -> None:
        self.root = root
        pass
