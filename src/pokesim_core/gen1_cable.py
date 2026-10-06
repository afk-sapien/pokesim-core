"""Explicit Gen1 virtual-cable transport over verified ROM hook locations.

Applications own participant selection, scheduling, files, and transaction commit.
The caller supplies a Core emulator and verified build symbols.
"""
from collections import Counter, deque


class CableError(RuntimeError):
    """A speculative link session cannot be adopted."""


def checked(condition, message):
    if not condition:
        raise CableError(message)


class CableEndpoint:
    def __init__(self, emulator, symbols, max_queue=4):
        if type(max_queue) is not int or max_queue < 1:
            raise ValueError("max_queue must be positive")
        self.pb = emulator
        self.sym = symbols
        self.peer = None
        self.parked = None
        self.pending = None
        self.inbox = {'byte': deque(), 'nybble': deque()}
        self.max_queue = max_queue
        self.counts = Counter()
        self.frame = 0
        self.hooks = []
        self.attached = False
        self.stopped = False
        self.park_original = bytes(self.pb.memory[0, 0x3ff0:0x3ff2])
        checked(self.park_original == bytes(2), 'Parking address is not verified padding')

    def get(self, key):
        return self.pb.memory[self.sym[key][1]]

    def put_transport(self, key, value):
        self.pb.memory[self.sym[key][1]] = value

    def hook(self, name, callback):
        bank, addr = self.sym[name]
        self.pb.hook_register(bank, addr, callback, None)
        self.hooks.append((bank, addr))

    def attach(self, role, enabled=True):
        checked(not self.attached and self.peer is not None, 'Invalid cable attachment')
        checked(role in (1, 2), 'Invalid clock role')
        self.attached = True
        self.pb.memory[0, 0x3ff0] = 0x18
        self.pb.memory[0, 0x3ff1] = 0xfe
        if enabled:
            def connect(_):
                self.counts['connect'] += 1
                self.put_transport('hSerialConnectionStatus', role)
            self.hook('CableClubNPC.establishConnectionLoop', connect)
            self.hook('Serial_ExchangeByte', lambda _: self.exchange('byte', 'hSerialSendData'))
            self.hook('Serial_SyncAndExchangeNybble',
                      lambda _: self.exchange('nybble', 'wSerialExchangeNybbleSendData'))
        for key in ('CableClub_DoBattleOrTrade', 'TradeCenter_SelectMon', 'TradeCenter_Trade',
                    'TradeCenter_Trade.tradeCompleted', 'SavePartyAndDexData', 'ReturnToCableClubRoom'):
            self.hook(key, lambda _, key=key: self.counts.update([key]))

    def exchange(self, kind, source):
        checked(self.peer is not None, 'Missing cable peer')
        self.counts[kind + '_calls'] += 1
        if self.pending is None:
            queue = self.peer.inbox[kind]
            checked(len(queue) < self.max_queue, 'Cable message queue overflow')
            queue.append(self.get(source))
            self.pending = kind
        checked(self.pending == kind, 'Cable exchange ordering mismatch')
        if not self.inbox[kind]:
            rf = self.pb.register_file
            checked(0xc000 <= rf.SP < 0xfffe, 'Invalid cable return stack')
            self.parked = (rf.PC, rf.SP, self.pb.memory[0xffff])
            self.pb.memory[0xffff] = 0
            rf.PC = 0x3ff0
            return
        value = self.inbox[kind].popleft()
        self.pending = None
        self.counts[kind + '_exchanged'] += 1
        if kind == 'nybble':
            self.put_transport('wSerialSyncAndExchangeNybbleReceiveData', value)
            self.put_transport('wSerialExchangeNybbleReceiveData', value)
        else:
            self.put_transport('hSerialReceiveData', value)
            self.put_transport('hSerialReceivedNewData', 0)
        rf = self.pb.register_file
        checked(0xc000 <= rf.SP < 0xfffe, 'Invalid cable return stack')
        target = self.pb.memory[rf.SP] | self.pb.memory[rf.SP + 1] << 8
        checked(0 < target < 0x8000 and target != 0x3ff0, 'Invalid cable return address')
        rf.A = value
        rf.PC = target
        rf.SP += 2

    def tick(self):
        if self.parked is not None:
            if not self.inbox[self.pending]:
                return False
            pc, sp, interrupt_mask = self.parked
            checked(self.pb.register_file.SP == sp, 'Parked CPU stack changed')
            checked(self.pb.memory[0xffff] == 0, 'Parked interrupt mask changed')
            self.pb.register_file.PC = pc
            self.pb.memory[0xffff] = interrupt_mask
            self.parked = None
        checked(self.pb.tick(1, True), 'Emulator stopped unexpectedly')
        self.frame += 1
        return True

    def release_buttons(self):
        for button in ('a', 'b', 'start', 'select', 'up', 'down', 'left', 'right'):
            self.pb.button_release(button)

    def detach(self):
        checked(self.parked is None and self.pending is None,
                'Cannot export a pending cable exchange')
        checked(all(not queue for queue in self.inbox.values()), 'Undrained cable messages')
        for bank, addr in self.hooks:
            self.pb.hook_deregister(bank, addr)
        self.hooks.clear()
        self.pb.memory[0, 0x3ff0] = self.park_original[0]
        self.pb.memory[0, 0x3ff1] = self.park_original[1]
        self.attached = False
        self.release_buttons()

    def stop(self):
        if not self.stopped:
            self.pb.stop(save=False)
            self.stopped = True
