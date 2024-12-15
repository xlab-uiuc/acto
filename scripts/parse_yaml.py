import ruamel.yaml
import ruamel.yaml.comments


def process_container(container: ruamel.yaml.comments.CommentedMap):
    schema = {
        "type": "object",
    }
    buf: list[ruamel.yaml.CommentToken] = []
    for comments in container.ca.comment:
        if comments is not None:
            for comment in comments:
                assert isinstance(comment, ruamel.yaml.CommentToken)
                if (
                    len(buf) > 0
                    and buf[-1].start_mark.line != comment.start_mark.line - 1
                ):
                    # Empty line between comments, reset buffer
                    buf = []
                buf.append(comment)

    for key, value in container.items():
        if isinstance(value, ruamel.yaml.comments.CommentedMap):
            schema[key] = process_container(value)
        elif isinstance(value, ruamel.yaml.comments.CommentedSeq):
            schema[key] = process_array(value)
        else:
            schema[key] = process_chunk(value)
    return schema


yaml = ruamel.yaml.YAML(typ="rt")

with open("cassandra.yaml", "r", encoding="utf-8") as f:
    data: ruamel.yaml.comments.CommentedMap = yaml.load(f)

    print(type(data))
    print(type(data.ca.comment))

    for k, v in data.ca.items.items():
        print(k, v)

    # for comment in data.ca.comment:
    #     print(comment)
