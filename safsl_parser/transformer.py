'''
Created on Jul 25, 2026

@author: haris
'''

from lark import Transformer
from lxml import etree 

from safsl_ast.nodes import (
    Specification,
    ProcessNode,
    InterfaceNode,
    TerminalNode,
    PortNode,
    PredicateNode,
    BodyNode,
    AssignmentNode,
    IfNode,
    ExpressionStatement,
    Identifier,
    Literal,
    Operation,
    PropertyReference,
    SubmodelReference,
    SubmodelElementReference,
    Reference,
    ElementReference,
    PropertyNode,
    RangeNode
)
from html5rdf._ihatexml import name

class AASResolver:

    def __init__(self, submodels):
        self.submodels = submodels


    def resolve(self, reference):

        current = self.submodels[reference.submodel]

        # unwrap dictionary wrapper
        if isinstance(current, dict):
            current = current[reference.submodel]

        for part in reference.path:

            if hasattr(current, "elements"):
                current = current.elements[part]

            else:
                raise Exception(
                    f"Cannot resolve {part}"
                )

        return current



class SAFSLTransformer(Transformer):

    def specification(self, items):
    
        name = str(items[0])
    
        submodels = []
        references = []
        processes = []
    
        for item in items[1:]:
    
            if isinstance(item, SubmodelReference):
                submodels.append(item)
    
            elif isinstance(item, ProcessNode):
                processes.append(item)
    
            elif isinstance(item, SubmodelElementReference):
                references.append(item)
    
    
        return Specification(
            name=name,
            submodels=submodels,
            references=references,
            processes=processes
        )

    def reference_path(self, items):
        return [str(x) for x in items]


    def process(self, items):

        name = str(items[0])

        interface = items[1]
        body = items[2]


        evolution = None

        if len(items) > 3:
            evolution = items[3]

        return ProcessNode(
            name=name,
            interface=interface,
            body=body,
            evolution=evolution
        )

    def interface_decl(self,items):

        terminals=[]
        ports=[]
        predicates=[]
        property_decls = []
        range_decls = []

        for item in items:

            if isinstance(item,TerminalNode):
                terminals.append(item)

            elif isinstance(item,PortNode):
                ports.append(item)

            elif isinstance(item,PredicateNode):
                predicates.append(item)
            
            elif isinstance(item,PropertyNode):
                property_decls.append(item)

            elif isinstance(item,RangeNode):
                range_decls.append(item)                

        return InterfaceNode(
            terminals=terminals,
            ports=ports,
            predicates=predicates,
            properties=property_decls,
            ranges=property_decls
        )



    def terminal_decl(self,items):

        return TerminalNode(
            direction=str(items[0]),
            name=str(items[1])
        )
    
    def port_reference(self, items):
        return items[0]

    def port_decl(self, items):
        
        reference = None
        if len(items) == 3:
            reference = Reference(
                path=items[2]
            )
            
        return PortNode(
            direction=str(items[0]),
            name=str(items[1]),
            reference=reference
        )



    def predicate_decl(self,items):

        return PredicateNode(
            name=str(items[0]),
            terminal=str(items[1]),
            condition=items[2]
        )

    
    def property_declaration(self,items):
        return PropertyNode(
                name = str(items[1]).strip('"'),
                value = str(items[6]).strip('"'),
                semanticId = str(items[5]).strip('"')
            )


    def body_decl(self,items):

        return BodyNode(
            statements=list(items)
        )

    def assignment_stmt(self,items):
        
        return AssignmentNode(
            operator = str(items[0]),
            target = items[1][0].name,
            value = ExpressionStatement(items[1][1])
            )


    def expression_stmt(self,items):

        return ExpressionStatement(
            expression=items[0]
        )



    def if_stmt(self,items):

        condition=items[0]

        statements=items[1:]

        return IfNode(
            condition=condition,
            statements=statements
        )


    def qualified_identifier(self,items):

        return Identifier(
            ".".join(
                str(x)
                for x in items
            )
        )


    def boolean_expression(self,items):

        return Operation(

            operator=str(items[0]),

            operands=list(items[1:])
        )



    def relational_expression(self,items):

        return Operation(

            operator=str(items[0]),

            operands=list(items[1:])
        )



    def arithmetic_expression(self,items):

        return Operation(

            operator=str(items[0].value),

            operands=[x for x in items[1]]
        )


    def IDENTIFIER(self,token):

        return str(token)


    def STRING(self,token):

        return str(token)
    
    def literal(self, items):
        token = items[0]
    
        if token.type == "BOOLEAN":
            return Literal(token == "True")
    
        elif token.type == "NUMBER":
            return Literal(float(token))
    
        elif token.type == "STRING":
            return Literal(token[1:-1])   # remove quotes

   
    def property_ref_decl(self, items):
        
        ref_path  = items[1]
    
        return PropertyReference(
            idShort=str(items[0]),
            submodel=ref_path[0],#str("CPrp"),
            value=str(items[0]),
            path=ref_path[1:]
        )

    def relational_call(self, items):
    
        operator = str(items[0])
    
        operands = items[1]
    
        return Operation(
            operator=operator,
            operands=operands
        )

    def expression_list(self, items):
        return list(items)


    def boolean_call(self, items):
    
        operator = str(items[0])
    
        operands = items[1]
    
        return Operation(
            operator=operator,
            operands=operands
        )



class QUDTResolver:

    def __init__(self, qudt_model):
        self.qudt = qudt_model


    def resolve_unit(self, semantic_id):

        if semantic_id in self.qudt:
            return self.qudt[semantic_id]

        return None

class SemanticResolver:

    def resolve(self, reference):

        if not reference.resolved:
            return


        semantic_id = (
            reference.resolved.semantic_id
        )


        if semantic_id:

            reference.semantic_id = semantic_id

        else:

            reference.semantic_id = None
