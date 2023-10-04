import sys
import typing
from enum import Enum


def read_bench(filename):
    with open(filename, 'r') as file:
        lines = file.readlines()

    gates_dict: typing.Dict[str, int] = {}
    inputs, outputs, gates = [], [], []
    num_outputs = 0
    num_gates = 1
    for line in lines:
        line = line.strip()
        if line.startswith('INPUT'):
            name = line.split('(')[1].split(')')[0]
            inputs.append(name)
            gates.append(Gate(name, Op.INPUT, line.strip(), [name]))
            gates_dict[name] = num_gates
            num_gates += 1

        elif line.startswith('OUTPUT'):
            name = line.split('(')[1].split(')')[0]
            outputs.append(name)
            gates.insert(num_outputs, Gate(name, Op.OUTPUT, line.strip(), []))
            gates_dict[name] = 0
        elif '=' in line:
            gate_name, gate_expression = line.split('=')
            gate_name = gate_name.strip()
            gate_expression = gate_expression.strip()
            gate_inputs = gate_expression.split('(')[1].split(')')[0].split(',')
            if gate_name not in gates_dict:
                gates.append(Gate(gate_name, from_name(gate_expression.split('(')[0]), gate_expression,
                                  list(map(lambda x: x.strip(), gate_inputs))))
                gates_dict[gate_name] = num_gates
            elif gate_name == outputs[0]:
                gates[0].op = from_name(gate_expression.split('(')[0])
                gates[0].expression = gate_expression
                gates[0].expression_inputs = list(map(lambda x: x.strip(), gate_inputs))
            else:
                raise Exception()
            num_gates += 1

    return inputs, outputs, gates, gates_dict


class Op(Enum):
    INPUT = 1,
    OUTPUT = 2,
    NOT = 3,
    AND = 4,
    OR = 5,
    XOR = 6,
    EQ = 7,
    ZERO = 8,
    ONE = 9,


def from_name(name: str) -> Op:
    if name == "INPUT":
        return Op.INPUT
    if name == "OUTPUT":
        return Op.OUTPUT
    if name == "NOT":
        return Op.NOT
    if name == "AND":
        return Op.AND
    if name == "OR":
        return Op.OR
    if name == "XOR":
        return Op.XOR


class Gate:
    def __init__(self, name: str,
                 op: Op,
                 expression: str,
                 expression_inputs: typing.List[str]):
        self.name = name
        self.op: Op = op
        self.expression = expression
        self.expression_inputs = expression_inputs

    def __str__(self):
        return f"{self.name}, {str(self.op)}, {str(self.expression_inputs)}"


class Scheme:
    def __init__(self,
                 gates: typing.List[Gate],
                 gates_dict: typing.Dict[str, int],
                 inputs: typing.List[str],
                 outputs: typing.List[str]):
        self.inputs = inputs
        self.outputs = outputs

        assert len(self.outputs) == 1

        self.gates = gates
        self.gates_dict = gates_dict
        self.used = [False] * len(gates)

        self.inverse_gates_dict = {x: y for y, x in gates_dict.items()}

        n = len(self.gates)
        tree = [[] for i in range(n)]

    def simplify(self):
        self.dfs_unused()

    def dfs_unused(self):
        stack = list(range(len(self.outputs)))
        for i in range(len(self.outputs)):
            self.used[i] = True

        while stack:
            top = stack.pop()
            for v in self.gates[top].expression_inputs:
                if not self.used[self.gates_dict[v]]:
                    self.used[self.gates_dict[v]] = True
                    stack.append(self.gates_dict[v])

        new_gates = list(self.gates[j] for j in range(len(self.gates)) if self.used[j])
        new_inputs = list(x for x in self.inputs if self.used[self.gates_dict[x]])
        new_gates_dict = {new_gates[ij].name: ij for ij in range(len(new_gates))}

        self.gates_dict = new_gates_dict
        self.inputs = new_inputs
        self.gates = new_gates
        self.inverse_gates_dict = {x: y for (y, x) in self.gates_dict.items()}
        self.used = [False] * (len(self.gates))

    def gate_by_name(self, s: str) -> Gate:
        return self.gates[self.gates_dict[s]]

    @staticmethod
    def calc(param: typing.List, op: Op):
        if len(param) == 1:
            # only Not
            return Scheme.const_2_enum(1 - param[0])
        [x, y] = param
        if op == Op.XOR:
            return Scheme.const_2_enum(x ^ y)
        if op == Op.AND:
            return Scheme.const_2_enum(x & y)
        if op == Op.OR:
            return Scheme.const_2_enum(x | y)

    @staticmethod
    def const_2_enum(x_: int):
        if x_ == 0:
            return Op.ZERO
        return Op.ONE

    def calculate_constants(self, idx):
        if self.gates[idx].op == Op.INPUT:
            return 0

        # recursive call
        for v in self.gates[idx].expression_inputs:
            self.calculate_constants(self.gates_dict[v])
        if len(self.gates[idx].expression_inputs) == 0:
            return 0
        if len(self.gates[idx].expression_inputs) == 1:
            if self.gates[idx].op == Op.EQ:
                if self.gate_by_name(self.gates[idx].expression_inputs[0]).op in {Op.ONE, Op.ZERO}:
                    self.gates[idx].op = self.gate_by_name(self.gates[idx].expression_inputs[0]).op
                    self.gates[idx].expression_inputs = []
                    self.gates[idx].expression = "ZERO" if self.gates[idx].op == Op.ZERO else "ONE"
            elif self.gates[idx].op == Op.ZERO:
                pass
            elif self.gates[idx].op == Op.ONE:
                pass
            if self.gates[idx].op == Op.NOT:
                if self.gate_by_name(self.gates[idx].expression_inputs[0]).op in {Op.ONE, Op.ZERO}:
                    parent = self.gate_by_name(self.gates[idx].expression_inputs[0]).op
                    self.gates[idx].op = Op.ONE if parent == Op.ZERO else Op.ZERO
                    self.gates[idx].expression_inputs = []
                    self.gates[idx].expression = "ZERO" if self.gates[idx].op == Op.ZERO else "ONE"
        else:
            if self.gate_by_name(self.gates[idx].expression_inputs[0]).op in {Op.ONE, Op.ZERO} and \
                    self.gate_by_name(self.gates[idx].expression_inputs[1]).op in {Op.ONE, Op.ZERO}:
                one = 1 if self.gate_by_name(self.gates[idx].expression_inputs[0]).op == Op.ONE else 0
                two = 1 if self.gate_by_name(self.gates[idx].expression_inputs[1]).op == Op.ONE else 0
                self.gates[idx].op = Scheme.calc([one, two], self.gates[idx].op)
                self.gates[idx].expression = "ZERO" if self.gates[idx].op == Op.ZERO else "ONE"
                self.gates[idx].expression_inputs = []

            if self.gates[idx].op == Op.XOR:
                if self.gate_by_name(self.gates[idx].expression_inputs[0]).name == \
                        self.gate_by_name(self.gates[idx].expression_inputs[1]).name:
                    self.gates[idx].op = Op.ZERO
                    self.gates[idx].expression = "ZERO" if self.gates[idx].op == Op.ZERO else "ONE"
                    self.gates[idx].expression_inputs = []

            if self.gates[idx].op == Op.AND:
                if self.gate_by_name(self.gates[idx].expression_inputs[0]).name == \
                        self.gate_by_name(self.gates[idx].expression_inputs[1]).name:
                    self.gates[idx].op = Op.EQ
                    self.gates[idx].expression = f"EQ{self.gate_by_name(self.gates[idx].expression_inputs[0]).name}"
                    self.gates[idx].expression_inputs = [self.gate_by_name(self.gates[idx].expression_inputs[0]).name]

            if self.gates[idx].op == Op.OR:
                if self.gate_by_name(self.gates[idx].expression_inputs[0]).op == Op.ONE or \
                        self.gate_by_name(self.gates[idx].expression_inputs[1]).op == Op.ONE:
                    self.gates[idx].op = Op.ONE
                    self.gates[idx].expression = "ZERO" if self.gates[idx].op == Op.ZERO else "ONE"
                    self.gates[idx].expression_inputs = []
            if self.gates[idx].op == Op.AND:
                if self.gate_by_name(self.gates[idx].expression_inputs[0]).op == Op.ZERO or \
                        self.gate_by_name(self.gates[idx].expression_inputs[1]).op == Op.ZERO:
                    self.gates[idx].op = Op.ZERO
                    self.gates[idx].expression = "ZERO" if self.gates[idx].op == Op.ZERO else "ONE"
                    self.gates[idx].expression_inputs = []


if __name__ == "__main__":
    args = sys.argv
    args.pop(0)

    gates = (read_bench("test2.bench"))
    scheme = Scheme(gates[2], gates[3], gates[0], gates[1])
    n = len(scheme.outputs)
    for i in range(n):
        scheme.calculate_constants(i)
    scheme.simplify()
    for n in scheme.gates:
        print(n)
