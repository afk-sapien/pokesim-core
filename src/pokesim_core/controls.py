"""Bounded controller macros for English Red/Blue. No memory writes.

Callers supply observation and controller adapters. Every input passes through
send or choose, preserving the consumer's frame budget, recording and locking.
Party slots are zero based. These helpers never decide which Pokemon to train.
"""
from dataclasses import dataclass, field
from collections.abc import Callable, Mapping
import re

from .gen1 import read_bag, read_party
from .gen1_ui import read_screen
from .menus import menu_options

RESTORATIVE_ITEMS = frozenset((11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 52, 53, 54, 82, 83))


def normalize(text):
    return re.sub('[^A-Z0-9]', '', text.upper().replace('É', 'E'))


def identity(mon):
    return mon['species'], mon['trainer_id'], tuple(mon['dvs']), mon['nick']


def panel(memory, ui, item_labels):
    """Identify only observed menus needed for these mechanical commands."""
    if ui['kind'] in ('overworld', 'battle_menu', 'move_menu', 'dialogue', 'transition'):
        return ui['kind']
    if ui['kind'] != 'menu':
        return 'unknown'
    choices = {normalize(x) for x in ui['visible_choices']}
    if {'USE', 'TOSS'} <= choices:
        return 'item_action'
    if {'SWITCH', 'STATS', 'CANCEL'} <= choices:
        return 'party_action'
    if {'ITEM', 'EXIT', 'SAVE'} <= choices:
        return 'pause'
    if {'YES', 'NO'} <= choices:
        return 'switch_prompt' if 'CHANGE POK' in ' '.join(ui['text']).upper() else 'unknown'
    options = menu_options(memory, read_screen(memory), ui['kind'])
    if options and options[0]['text'].startswith('1: ') and ui['cursor_tile'][0] == 0:
        return 'item_target' if 'USE ITEM' in ' '.join(ui['text']).upper() else 'party'
    if (memory[0xCC25] == 5 and memory[0xCC24] == 4 and ui['cursor_tile']
            and ui['cursor_tile'][0] == 5 and ui['cursor_tile'][1] in (4, 6, 8)):
        bag = read_bag(memory)
        index = memory[0xCC26] + memory[0xCC36]
        if index < len(bag):
            label = item_labels.get(str(bag[index][0]), '')
            if isinstance(label, str) and normalize(ui['selected_text'] or '') == normalize(label):
                return 'bag'
        elif normalize(ui['selected_text'] or '') == 'CANCEL':
            return 'bag'
    return 'unknown'


@dataclass
class ControllerPort:
    """Adapter to a serialized, budgeted consumer controller.

    send(button, held_frames, released_frames) and choose(visible_label) return
    False on budget exhaustion. Both must account for every emulated frame.
    observe returns the visible UI kind, text, cursor_tile, selected_text and
    visible_choices. continue_ready must only approve continue-only text waits.
    """
    memory: object
    send: Callable
    choose: Callable
    observe: Callable
    frame: Callable
    stopped: Callable = lambda: False
    continue_ready: Callable = lambda: False
    item_labels: Mapping = field(default_factory=dict)
    read_party: Callable = read_party
    read_bag: Callable = read_bag
    panel: Callable = panel
    menu_rows: Callable | None = None


def use_item(port, item_id, party_slot):
    """Use one supported restorative on an explicitly selected owned Pokemon."""
    if type(item_id) is not int or item_id not in RESTORATIVE_ITEMS:
        raise ValueError('Only supported restorative item IDs are accepted')
    return _run(port, party_slot, item_id)


def switch_pokemon(port, party_slot):
    """Switch the active battler or move an owned Pokemon to the party lead."""
    return _run(port, party_slot, None)


def _run(port, slot, item):
    if type(slot) is not int or not 0 <= slot < 6:
        raise ValueError('Party slot must be an integer from 0 through 5')
    result = {}
    _execute(port, slot, item, result)
    result.setdefault('outcome', 'Controller stopped before confirming the requested effect.')
    return result


def _execute(port, slot, item, result):
    send, choose = port.send, port.choose
    memory = port.memory
    party = port.read_party(memory)
    if slot >= len(party):
        result['outcome'] = 'Party slot is unavailable. No input sent.'
        return
    target = identity(party[slot])
    battle = memory[0xD057] in (1, 2)
    quantity = dict(port.read_bag(memory)).get(item, 0) if item else None
    if item and not quantity:
        result['outcome'] = 'Requested item is not in the bag. No input sent.'
        return
    if not item and battle and (not party[slot]['hp'] or memory[0xCC2F] == slot):
        result['outcome'] = 'Requested Pokemon is fainted or already active. No input sent.'
        return
    if not item and not battle and slot == 0:
        result['outcome'] = 'Requested Pokemon is already the lead. No input sent.'
        return
    result['shortcut'] = {'kind':'use_item' if item is not None else 'switch_pokemon', 'party_slot':slot + 1, 'item_id':item,
                          'completed':False, 'item_consumed':False}
    phase = 'open'
    ready_after = port.frame()
    committed = False
    last = None
    repeats = 0

    def tap(button):
        nonlocal ready_after
        ok = send(button, 8, 24)
        ready_after = port.frame() + 12
        return ok

    def select_party(destination):
        current = port.observe()['cursor_tile']
        if current != [0, 1 + 2 * memory[0xCC26]]:
            return False
        return tap('a' if memory[0xCC26] == destination else 'down' if memory[0xCC26] < destination else 'up')

    for _ in range(200):
        if port.stopped():
            break
        ui = port.observe()
        current = port.panel(memory, ui, port.item_labels)
        members = port.read_party(memory)
        consumed = item is not None and dict(port.read_bag(memory)).get(item, 0) < quantity
        switched = not item and ((battle and memory[0xCC2F] == slot)
                                  or (not battle and members and identity(members[0]) == target))
        result['shortcut']['item_consumed'] = consumed
        if consumed or switched:
            phase = 'finish'
            result['shortcut']['completed'] = True
        elif slot >= len(members) or identity(members[slot]) != target:
            result['outcome'] = 'Party changed before the requested selection. Stopped.'
            return
        if port.frame() < ready_after:
            if not send(None, min(12, ready_after - port.frame()), 0):
                break
            continue
        if current in ('dialogue', 'transition'):
            if current == 'dialogue' and port.continue_ready():
                if not tap('a'):
                    break
            elif not send(None, 30, 0):
                break
            continue
        signature = (phase, current, ui['cursor_tile'], memory[0xCC26], memory[0xCC36])
        repeats = repeats + 1 if signature == last else 0
        last = signature
        if repeats >= (24 if committed else 8):
            result['outcome'] = 'Menu did not respond. Stopped without repeating the requested effect.'
            return
        if phase == 'finish':
            if not battle and current in ('bag', 'pause', 'party', 'party_action', 'item_action'):
                if not tap('b'):
                    break
                continue
            result['outcome'] = 'Used the requested item.' if item else 'Switched to the requested Pokemon.'
            return
        if phase == 'open':
            if current == 'overworld' and not battle:
                if not tap('start'):
                    break
            elif current == 'battle_menu':
                if not choose('ITEM' if item else 'PKMN'):
                    return
                phase = 'bag' if item else 'party'
            elif current == 'pause':
                if not choose('ITEM' if item else 'POKéMON'):
                    return
                phase = 'bag' if item else 'party'
            elif current == 'bag' and item:
                phase = 'bag'
            elif current == 'party' and not item:
                phase = 'party'
            elif current == 'switch_prompt' and battle and not item:
                if not choose('YES'):
                    return
                phase = 'party'
            elif current in ('move_menu', 'bag', 'pause', 'item_action', 'item_target', 'party', 'party_action'):
                if not tap('b'):
                    break
            else:
                result['outcome'] = 'Unsupported starting menu. No further input sent.'
                return
        elif phase == 'bag' and current == 'bag':
            bag = port.read_bag(memory)
            destination = next((i for i, entry in enumerate(bag) if entry[0] == item), None)
            selected = memory[0xCC26] + memory[0xCC36]
            if destination is None:
                result['outcome'] = 'Requested item disappeared. Stopped.'
                return
            if selected == destination:
                if not tap('a'):
                    break
                phase = 'item_use'
            elif not tap('down' if selected < destination else 'up'):
                break
        elif phase == 'item_use':
            if current == 'item_action':
                if not choose('USE'):
                    return
                phase = 'item_target'
            elif current in ('item_target', 'party'):
                phase = 'item_target'
            elif current == 'bag':
                if not send(None, 30, 0):
                    break
            else:
                result['outcome'] = 'Item did not open a target menu. Stopped.'
                return
        elif phase in ('item_target', 'party') and current in ('item_target', 'party'):
            selected = memory[0xCC26] == slot
            if not select_party(slot):
                break
            if selected:
                committed = True
                phase = 'item_confirmed' if item else 'party_confirmed'
        elif phase == 'party_confirmed' and current == 'party_action':
            if not choose('SWITCH'):
                return
            phase = 'switch_confirmed' if battle else 'lead_destination'
        elif phase == 'lead_destination' and current == 'party':
            selected = memory[0xCC26] == 0
            if not select_party(0):
                break
            if selected:
                phase = 'switch_confirmed'
        elif committed:
            if current in ('party', 'item_target', 'party_action'):
                if port.continue_ready():
                    if not tap('a'):
                        break
                elif not send(None, 30, 0):
                    break
            else:
                result['outcome'] = 'Requested selection returned without a confirmed effect. No second use attempted.'
                return
        else:
            result['outcome'] = 'Unexpected menu. Stopped before any unrequested choice.'
            return
    result['outcome'] = 'Shortcut stopped at its controller or run budget. Inspect current state before continuing.'
