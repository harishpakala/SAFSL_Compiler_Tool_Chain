'''
Created on Jul 25, 2026

@author: haris
'''
from dataclasses import dataclass, field
from typing import List, Optional, Any
from typing import Dict

class ASTNode:
    pass


class Statement(ASTNode):
    pass


class Expression(ASTNode):
    pass


@dataclass
class Specification(ASTNode):
    name: str
    submodels: List["SubmodelReference"] = field(default_factory=list)
    references: List["SubmodelElementReference"] = field(default_factory=list)
    processes: List["ProcessNode"] = field(default_factory=list)



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
    reference: Optional["Reference"] = None
    

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
class Reference:
    path: list[str]

@dataclass
class ElementReference:
    path: list[str]
    resolved: Optional[object] = None

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


@dataclass
class SubmodelElementReference:
    idShort: str
    submodel: str
    path: list[str]
    element_type: str
    resolved: object = None
    semantic_id: str = None


@dataclass
class RangeReference(SubmodelElementReference):
    min: str = None
    max: str = None

    def __init__(
        self,
        idShort: str,
        submodel: str,
        path: list[str],
        min: str = None,
        max: str = None
    ):
        super().__init__(
            idShort=idShort,
            submodel=submodel,
            path=path,
            element_type="Range"
        )
        self.min = min
        self.max = max

@dataclass
class PropertyReference(SubmodelElementReference):

    value: str = None

    def __init__(
        self,
        idShort: str,
        submodel: str,
        path: list[str],
        value: str = None,
        semantic_id: str = None
    ):
        super().__init__(
            idShort=idShort,
            submodel=submodel,
            path=path,
            element_type="Property",
            semantic_id=semantic_id
        )
        self.value = value

@dataclass
class SMCReference(SubmodelElementReference):

    elements: dict = field(default_factory=dict)

    def __init__(
        self,
        idShort: str,
        submodel: str,
        path: list,
        elements=None
    ):

        super().__init__(
            idShort=idShort,
            submodel=submodel,
            path=path,
            element_type="SubmodelElementCollection"
        )

        self.elements = elements or {}



@dataclass
class SubmodelReference:
    name: str
    identifier: str
    elements: Dict[str, "SubmodelElementReference"] = field(default_factory=dict)
