"""Observed, resumable name entry through the English Red/Blue keyboard."""
from typing import NamedTuple

from .gen1_ui import read_screen


class ButtonAction(NamedTuple):
    button: str | None
    hold: int = 6
    gap: int = 24


def validate_name(name, *, limit=10):
    if type(limit) is not int or not 1 <= limit <= 10:
        raise ValueError('Name limit must be from 1 through 10')
    if not isinstance(name, str) or not 1 <= len(name) <= limit or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' for c in name):
        raise ValueError(f'Name must contain 1 through {limit} uppercase ASCII letters')
    return name


def name_step(rows, cursor, name, *, limit=10):
    """Return the next keyboard action. Return None outside the naming screen.

    Read back entered letters on every call, including after restoring a save.
    The caller owns name selection and whether to accept a nickname prompt.
    """
    validate_name(name, limit=limit)
    if not any(row[2:19:2] in ('ABCDEFGHI', 'abcdefghi') for row in rows):
        return None
    entered = rows[2][10:10 + limit].strip()
    if not name.startswith(entered):
        return ButtonAction('b')
    if entered == name:
        return ButtonAction('start')
    if any(row[2:19:2] == 'abcdefghi' for row in rows):
        return ButtonAction('select')
    if cursor is None:
        return ButtonAction(None, 0, 12)
    offset = ord(name[len(entered)]) - ord('A')
    target_x, target_y = 1 + offset % 9 * 2, 5 + offset // 9 * 2
    x, y = cursor
    button = ('down' if y < target_y else 'up') if y != target_y else (
        ('right' if x < target_x else 'left') if x != target_x else 'a')
    return ButtonAction(button)


def enter_name(port, name, *, limit=10, max_actions=256):
    """Enter a supplied name through a ControllerPort, with a bounded result.

    Start on the naming keyboard. A successful result means the supplied text
    was observed and submitted and the keyboard subsequently closed.
    """
    validate_name(name, limit=limit)
    if type(max_actions) is not int or not 1 <= max_actions <= 1024:
        raise ValueError('max_actions must be from 1 through 1024')
    submitted = False
    for _ in range(max_actions):
        if port.stopped():
            break
        if port.observe()['kind'] == 'transition':
            if not port.send(None, 12, 0):
                break
            continue
        screen = read_screen(port.memory, raw_text=True)
        action = name_step(screen['rows'], screen['cursor'], name, limit=limit)
        if action is None:
            return {'completed': submitted, 'outcome': 'Name submitted.' if submitted else 'Naming keyboard is not open.'}
        if submitted:
            # Never submit twice if the game is still closing its keyboard.
            action = ButtonAction(None, 12, 0)
        if not port.send(*action):
            break
        submitted |= action.button == 'start'
    return {'completed': False, 'outcome': 'Name entry stopped at its controller budget.'}


def menu_button(current, target):
    """Choose one direction or confirmation for a zero based linear menu."""
    if any(type(value) is not int or value < 0 for value in (current, target)):
        raise ValueError('Menu positions must be nonnegative integers')
    return 'a' if current == target else 'down' if current < target else 'up'
