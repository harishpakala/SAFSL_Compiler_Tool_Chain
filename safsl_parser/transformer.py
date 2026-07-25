'''
Created on Jul 25, 2026

@author: haris
'''

from lark import Transformer

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
    Operation
)



class SAFSLTransformer(Transformer):


    # =================================================
    # Process
    # =================================================


    def specification(self, items):

        return Specification(
            processes=items
        )



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


        for item in items:

            if isinstance(item,TerminalNode):
                terminals.append(item)

            elif isinstance(item,PortNode):
                ports.append(item)

            elif isinstance(item,PredicateNode):
                predicates.append(item)


        return InterfaceNode(
            terminals=terminals,
            ports=ports,
            predicates=predicates
        )



    def terminal_decl(self,items):

        return TerminalNode(
            direction=str(items[0]),
            name=str(items[1])
        )



    def port_decl(self,items):

        binding=None

        if len(items)>2:
            binding=str(items[2])


        return PortNode(
            direction=str(items[0]),
            name=str(items[1]),
            binding=binding
        )



    def predicate_decl(self,items):

        return PredicateNode(
            name=str(items[0]),
            terminal=str(items[1]),
            condition=items[2]
        )




    def body_decl(self,items):

        return BodyNode(
            statements=list(items)
        )

    def assignment_stmt(self,items):

        return AssignmentNode(

            target=str(items[0]),

            operator=str(items[1]),

            value=items[2]
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


    def boolean_call(self,items):

        return Operation(

            operator=str(items[0]),

            operands=list(items[1:])
        )



    def relational_expr(self,items):

        return Operation(

            operator=str(items[0]),

            operands=list(items[1:])
        )



    def arithmetic_call(self,items):

        return Operation(

            operator=str(items[1]),

            operands=list(items[2:])
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
    
