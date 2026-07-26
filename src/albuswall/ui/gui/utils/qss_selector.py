#
"""
QSS Selector and Block Editor

This module provides the `QssBlockEditor` class for manipulating a single
qualified rule (selector + declaration block) in a Qt Style Sheet (QSS).
It also exports low‑level utility functions for parsing declarations,
normalizing selectors, matching selectors with various modes, and more.
"""

import re
import fnmatch
import tinycss2
from tinycss2 import ast
from typing import List, Optional, Dict
from dataclasses import dataclass

# ----------------------------------------------------------------------
# Public data structure: Declaration
# ----------------------------------------------------------------------
@dataclass
class Declaration:
    """
    Represents a single CSS declaration (property: value) inside a rule block.

    Attributes:
        name: Lowercased property name for case‑insensitive matching.
        raw_name_tokens: Original token(s) of the property name (preserves case).
        value_tokens: List of tokens representing the property value.
        start_index: Start index of this declaration in the content token list.
        end_index: End index (exclusive) of this declaration.
        has_semicolon: Whether the original declaration ended with a semicolon.
    """
    name: str
    raw_name_tokens: List
    value_tokens: List
    start_index: int
    end_index: int
    has_semicolon: bool = True


# ----------------------------------------------------------------------
# Low‑level utility functions (reusable and testable)
# ----------------------------------------------------------------------
def parse_declarations(content_tokens: List) -> List[Declaration]:
    """
    Extract all `Declaration` objects from a token list representing the
    content of a qualified rule (i.e., the block between `{` and `}`).

    Correctly handles nested parentheses, functions, and comments.

    Args:
        content_tokens: List of tokens from `tinycss2` parsing.

    Returns:
        List of `Declaration` objects in order of appearance.
    """
    declarations = []
    i = 0
    n = len(content_tokens)

    while i < n:
        # Skip whitespace and comments
        if content_tokens[i].type in ('whitespace', 'comment'):
            i += 1
            continue

        # A declaration must start with an identifier
        if content_tokens[i].type == 'ident':
            decl_start = i
            name_token = content_tokens[i]
            i += 1

            # Skip whitespace before colon
            while i < n and content_tokens[i].type in ('whitespace', 'comment'):
                i += 1

            # Must encounter a colon
            if not (i < n and content_tokens[i].type == 'literal' and content_tokens[i].value == ':'):
                continue
            i += 1  # skip colon

            # Skip whitespace after colon
            while i < n and content_tokens[i].type in ('whitespace', 'comment'):
                i += 1

            value_start = i
            nesting = 0
            semicolon = False

            while i < n:
                tok = content_tokens[i]
                # if tok.type == 'function' or (tok.type == 'literal' and tok.value == '('):
                if tok.type == 'literal' and tok.value == '(':
                    nesting += 1
                elif tok.type == 'literal' and tok.value == ')':
                    nesting = max(0, nesting - 1)
                elif tok.type == 'literal' and tok.value == ';' and nesting == 0:
                    semicolon = True
                    i += 1
                    break
                elif tok.type == 'literal' and tok.value == '}' and nesting == 0:
                    break
                i += 1

            value_end = i
            value_tokens = content_tokens[value_start:value_end]
            # Strip trailing whitespace/comments from value
            while value_tokens and value_tokens[-1].type in ('whitespace', 'comment'):
                value_tokens.pop()

            declarations.append(Declaration(
                name=name_token.value.lower(),
                raw_name_tokens=[name_token],
                value_tokens=value_tokens,
                start_index=decl_start,
                end_index=i,
                has_semicolon=semicolon
            ))
        else:
            i += 1

    return declarations


def replace_declaration(content_tokens: List, decl: Declaration,
                        new_value_tokens: List, new_name: Optional[str] = None) -> None:
    """
    Replace an existing declaration in‑place with a new property name (optional)
    and value.

    If `new_name` is provided and differs from the original property name,
    a new IdentToken is created with that name. Otherwise, the original
    `decl.raw_name_tokens` are reused to preserve original casing.

    Args:
        content_tokens: The token list of the declaration block (modified in place).
        decl: The `Declaration` object to replace.
        new_value_tokens: Token list for the new value.
        new_name: Optional new property name. If None, the original name is kept.
    """
    new_tokens = []

    # 选择使用新名称还是保留原 token
    if new_name is not None and new_name.lower() != decl.name:
        # 使用新名称创建 IdentToken
        new_tokens.append(ast.IdentToken(0, 0, new_name))
    else:
        # 复用原始 token，保留原有大小写和格式
        new_tokens.extend(decl.raw_name_tokens)

    new_tokens.append(ast.LiteralToken(0, 0, ':'))
    new_tokens.append(ast.WhitespaceToken(0, 0, ' '))
    new_tokens.extend(new_value_tokens)
    if decl.has_semicolon:
        new_tokens.append(ast.LiteralToken(0, 0, ';'))

    content_tokens[decl.start_index:decl.end_index] = new_tokens


def append_declaration(content_tokens: List, name: str, value_tokens: List) -> None:
    """
    Append a new declaration at the end of the declaration block.

    Automatically adds appropriate indentation (newline + 4 spaces) unless
    the block already ends with whitespace.

    Args:
        content_tokens: The token list of the declaration block (modified in place).
        name: Property name.
        value_tokens: Token list for the property value.
    """
    # Add a newline and indentation if the block doesn't end with whitespace/comment
    if content_tokens and content_tokens[-1].type not in ('whitespace', 'comment'):
        content_tokens.append(ast.WhitespaceToken(0, 0, '\n    '))
    else:
        content_tokens.append(ast.WhitespaceToken(0, 0, '    '))

    new_tokens = [
        ast.IdentToken(0, 0, name),
        ast.LiteralToken(0, 0, ':'),
        ast.WhitespaceToken(0, 0, ' '),
        *value_tokens,
        ast.LiteralToken(0, 0, ';')
    ]
    content_tokens.extend(new_tokens)


def normalize_selector(selector: str) -> str:
    """
    Normalize a selector string by collapsing whitespace and stripping edges.

    Args:
        selector: Raw selector string.

    Returns:
        Normalized selector (single spaces, no leading/trailing spaces).
    """
    return re.sub(r'\s+', ' ', selector.strip())


def selector_sort_key(selector: str) -> int:
    """
    Compute a numeric weight for a selector used to order rules when inserting
    new rules intelligently.

    Higher weight means the rule should appear later (more specific or complex).

    Args:
        selector: Selector string.

    Returns:
        Integer weight.
    """
    key = 0
    # Pseudo‑elements and special Qt indicators
    if '::' in selector or ':indicator' in selector or ':item' in selector:
        key += 60
    # Pseudo‑classes
    elif ':' in selector:
        key += 50
    # ID selector
    elif selector.startswith('#'):
        key += 40
    # Class selector
    elif selector.startswith('.'):
        key += 20
    # Attribute selector
    elif '[' in selector and ']' in selector:
        key += 30
    else:
        # Element selector or compound
        if re.match(r'^[a-zA-Z_][\w\-]*$', selector):
            key += 10
        else:
            key += 70   # complex selector
    return key


def get_selector_text(prelude_tokens: List) -> str:
    """
    Serialize the prelude token list (selector part) to a string.

    Args:
        prelude_tokens: Token list from a `qualified-rule`.

    Returns:
        Selector string with leading/trailing whitespace stripped.
    """
    return tinycss2.serialize(prelude_tokens).strip()


def matches_selector(rule_selector: str, target: str, mode: str) -> bool:
    # noinspection SpellCheckingInspection
    """
        Check whether a rule selector matches a target pattern according to `mode`.

        Supported modes:
            - 'exact':     Normalized strings are equal.
            - 'base':      Extract the base type (e.g., "QPushButton" from "QPushButton:hover").
            - 'wildcard':  Unix‑style wildcard matching (`fnmatch`).
            - 'regex':     Regular expression search.

        Args:
            rule_selector: The selector string from the rule.
            target: The pattern to match against.
            mode: One of the modes above.

        Returns:
            True if the rule selector matches the target.
        """
    if mode == 'exact':
        return normalize_selector(rule_selector) == normalize_selector(target)
    elif mode == 'base':
        base = re.split(r'[:#\[]', rule_selector)[0].strip()
        return base == target.strip()
    elif mode == 'wildcard':
        return fnmatch.fnmatch(rule_selector, target)
    elif mode == 'regex':
        return re.search(target, rule_selector) is not None
    else:
        raise ValueError(f"Unsupported match mode: {mode}")


# ----------------------------------------------------------------------
# QssBlockEditor: Editor for a single qualified rule
# ----------------------------------------------------------------------
class QssBlockEditor:
    """
    Lightweight editor for a single qualified rule (selector + declaration block).

    It allows querying and modifying properties, deleting them, and serialising
    the rule back to a string while preserving original formatting, comments,
    and whitespace as much as possible.

    Example:
        >>> from tinycss2 import parse_component_value_list
        >>> prelude = parse_component_value_list("QPushButton")
        >>> content = parse_component_value_list("background: red;")
        >>> editor = QssBlockEditor(prelude, content)
        >>> editor.set_property("color", "blue")
        >>> print(editor.serialize())
        QPushButton { background: red; color: blue; }
    """

    # Match mode constants (exposed for convenience)
    MATCH_EXACT = 'exact'
    MATCH_BASE = 'base'
    MATCH_WILDCARD = 'wildcard'
    MATCH_REGEX = 'regex'

    def __init__(self, prelude_tokens: List, content_tokens: List):
        """
        Initialize the editor with prelude and content token lists.

        Args:
            prelude_tokens: Token list for the selector part.
            content_tokens: Token list for the declaration block (between `{` and `}`).
        """
        self.prelude_tokens = prelude_tokens
        self.content_tokens = content_tokens
        self._declarations: List[Declaration] = []
        self._parse_declarations()

    # ---------- Internal parsing ----------
    def _parse_declarations(self) -> None:
        """Re‑parse the content tokens to refresh the declarations list."""
        self._declarations = parse_declarations(self.content_tokens)

    # ---------- Selector related ----------
    def get_selector(self) -> str:
        """Return the original selector string (as it appears in the source)."""
        return get_selector_text(self.prelude_tokens)

    def get_normalized_selector(self) -> str:
        """Return the selector string with collapsed whitespace."""
        return normalize_selector(self.get_selector())

    def matches(self, target: str, mode: str = MATCH_EXACT) -> bool:
        """
        Check if this rule's selector matches a target pattern.

        Args:
            target: The pattern to match.
            mode: Matching mode (see `matches_selector`).

        Returns:
            True if the selector matches.
        """
        return matches_selector(self.get_selector(), target, mode)

    # ---------- Property CRUD ----------
    def get_property(self, name: str) -> Optional[str]:
        """
        Get the value of a property as a string.

        Args:
            name: Property name (case‑insensitive).

        Returns:
            The property value string, or None if the property does not exist.
        """
        name_low = name.lower()
        for decl in self._declarations:
            if decl.name == name_low:
                return tinycss2.serialize(decl.value_tokens).strip()
        return None

    def get_property_names(self) -> List[str]:
        """Return a list of property names (lowercased) in this rule."""
        return [d.name for d in self._declarations]

    def get_all_properties(self) -> Dict[str, str]:
        """Return a dictionary mapping property names to their string values."""
        return {d.name: tinycss2.serialize(d.value_tokens).strip() for d in self._declarations}

    def set_property(self, name: str, value: str) -> None:
        """
        Set a property to a new value. If the property already exists, it is
        replaced; otherwise a new declaration is appended.

        The original formatting (indentation, comments) is preserved as much as
        possible.

        Args:
            name: Property name.
            value: New value (will be parsed into tokens).
        """
        name_low = name.lower()
        new_value_tokens = tinycss2.parse_component_value_list(value)

        for decl in self._declarations:
            if decl.name == name_low:
                replace_declaration(self.content_tokens, decl,
                                    new_value_tokens,
                                    name)
                self._parse_declarations()
                return

        # Property not found – append a new one
        append_declaration(self.content_tokens, name, new_value_tokens)
        self._parse_declarations()

    def delete_property(self, name: str) -> bool:
        """
        Delete a property from the rule.

        Args:
            name: Property name (case‑insensitive).

        Returns:
            True if the property was deleted, False if it did not exist.
        """
        name_low = name.lower()
        for decl in self._declarations:
            if decl.name == name_low:
                del self.content_tokens[decl.start_index:decl.end_index]
                self._parse_declarations()
                return True
        return False

    # ---------- Serialization ----------
    def serialize(self) -> str:
        """
        Serialize the entire rule (selector + block) back to a valid QSS string.

        Returns:
            The rule as a string, ready to be written to a file.
        """
        return tinycss2.serialize(self.prelude_tokens) + tinycss2.serialize(self.content_tokens)