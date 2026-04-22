from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class _Attrs:
    color: str | None = None
    bgcolor: str | None = None
    reverse: bool = False


class Style:
    def __init__(self, mapping: dict[str, str]):
        self.mapping = mapping

    @classmethod
    def from_dict(cls, mapping: dict[str, str]):
        return cls(mapping)

    def get_attrs_for_style_str(self, style_str: str) -> _Attrs:
        attrs = _Attrs()
        keys = [segment.replace("class:", "").strip() for segment in style_str.split() if segment.strip()]
        combined_key = " ".join(keys)
        ordered_keys = [*keys, combined_key] if combined_key else keys
        for key in ordered_keys:
            spec = self.mapping.get(key)
            if spec is None:
                continue
            for token in spec.split():
                if token == "noreverse":
                    attrs.reverse = False
                elif token.startswith("bg:"):
                    attrs.bgcolor = token[3:]
                elif token.startswith("#"):
                    attrs.color = token[1:]
        return attrs
