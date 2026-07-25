'''
Created on Jul 25, 2026

@author: haris
'''
from dataclasses import dataclass, field
from typing import List, Optional, Any


# =====================================================
# Base classes
# =====================================================

class ASTNode:
    pass


class Statement(ASTNode):
    pass


class Expression(ASTNode):
    pass


# =====================================================
# Process level
# =====================================================

@dataclass
class Specification(ASTNode):
    processes: List["ProcessNode"]


@dataclass
class ProcessNode(ASTNode):
    name: str
    interface: ["InterfaceNode" ] = None
    body: Optional["BodyNode"] = None
    evolution: Optional["EvolutionNode"] = None


@dataclass
class InterfaceNode(ASTNode):

    terminals: List["TerminalNode"] = field(default_factory=list)

    ports: List["PortNode"] = field(default_factory=list)

    predicates: List["PredicateNode"] = field(default_factory=list)

@dataclass
class TerminalNode(ASTNode):

    direction: str
    name: str



@dataclass
class PortNode(ASTNode):

    direction: str
    name: str
    binding: Optional[str] = None



@dataclass
class PredicateNode(ASTNode):

    name: str
    terminal: str
    condition: Expression

@dataclass
class BodyNode(ASTNode):

    statements: List[Statement]


@dataclass
class AssignmentNode(Statement):

    target: str
    operator: str
    value: Expression




@dataclass
class ExpressionStatement(Statement):

    expression: Expression

@dataclass
class Identifier(Expression):

    name: str



@dataclass
class Literal(Expression):

    value: Any



@dataclass
class Operation(Expression):

    operator: str
    operands: List[Expression]



@dataclass
class EvolutionNode(ASTNode):

    assumptions: List[Any]
    guarantees: List[Any]
    equations: List[Any]


@dataclass
class FunctionBlock:
    name: str
    terminals: list = field(default_factory=list)
    ports: list = field(default_factory=list)
    body: list = field(default_factory=list)


@dataclass
class IfNode(Statement):

    condition: Expression
    statements: List[Statement]



@dataclass
class ForeachNode(Statement):
    variable: str
    iterable: Expression
    statements: List[Statement]

@dataclass
class RelationalExpressionNode(Expression):
    operator: str
    left: Expression
    right: Expression

@dataclass
class BooleanExpressionNode(Expression):
    operator: str
    operands: List[Expression]


@dataclass
class ArithmeticExpressionNode(Expression):
    operator: str
    operands: List[Expression]

