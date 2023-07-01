from typing import Any, Tuple, List, Dict


def visit_dict(dic: Dict[str, Any], path: List[str]) -> Tuple[bool, Any]:
    if not path:
        return True, dic
    if not isinstance(dic, dict):
        return False, None
    if len(path) != 1:
        if path[0] not in dic:
            return False, None
        return visit_dict(dic[path[0]], path[1:])
    if path[0] not in dic:
        return False, None
    return True, dic[path[0]]
