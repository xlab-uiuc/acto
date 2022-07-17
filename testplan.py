import random


class TreeNode():

    def __init__(self, path: list) -> None:
        self.path = path

        self.parent = None
        self.children = {}
        self.testcases = []

        self.node_disabled = False
        self.subtree_disabled = False

    def add_child(self, key: str, child: 'TreeNode'):
        self.children[key] = child
        child.set_parent(self)

    def set_parent(self, parent: 'TreeNode'):
        self.parent = parent

    def add_testcases(self):
        pass

    def disable_node(self):
        '''This node will not be selected at this step'''
        self.node_disabled = True

    def disable_subtree(self):
        '''This node and its children will not be selected at this step'''
        self.subtree_disabled = True

    def disable_ancestors(self):
        parent = self.parent

        while parent != None:
            parent.disable_node()

        return

    def get_children(self) -> dict:
        return self.children

    def get_testcases(self) -> list:
        return self.testcases

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.children['ITEM']
        else:
            return self.children[key]

    def eligible_fields(self) -> list:
        '''Returns all eligible fields of this subtree
        
        a field is eligible if it is not disabled and has at least one testcase
        '''
        if self.subtree_disabled:
            return []

        ret = []
        if not self.node_disabled and len(self.testcases) > 0:
            ret.append(self)

        for child in self.children.values():
            ret.extend(child.eligible_fields())

        return ret

    def deepcopy(self):
        ret = TreeNode(self.path)
        for key, child in self.children.items():
            ret.add_child(key, child.deepcopy())

        return ret


class TestPlan():

    def __init__(self, root: TreeNode) -> None:
        self.root = root

    def select_fields(self, num_cases: int = 2):
        ret = []

        for i in range(num_cases):
            eligible_fields = self.root.eligible_fields()
            if len(eligible_fields) == 0:
                break

            field = random.choice(eligible_fields)
            field.disable_subtree()
            field.disable_ancestors()
            ret.append(field)

        return ret
