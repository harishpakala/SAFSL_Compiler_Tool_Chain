'''
Created on Jul 25, 2026

@author: haris
'''

from lxml.etree import Element, SubElement, tostring
from lxml import etree

from safsl_ast.nodes import AssignmentNode, IfNode, Identifier, Literal


algorithm = []


def generate_fb_xml(Safslprocess):

    root = Element( "FunctionBlock", { "name": "fb"})

    interface = SubElement(root, "InterfaceList")

    EventInputs = SubElement(interface, "EventInputs")
    EventOutputs = SubElement(interface, "EventOutputs")

    InputVars = SubElement(interface, "InputVars")
    OutputVars = SubElement(interface, "OutputVars")
    
    BasicFB = SubElement(root, "BasicFB")
    
    Algorithm = SubElement( BasicFB, "Algorithm", { "Name": "ALG", "Type":"ST" })
    ECC = SubElement(root, "ECC")
    SubElement(ECC, "ECState", { "name": "START", "Initial":"true"})

    body_state = SubElement(ECC,"ECState",{"name": "BODY",})
    
    SubElement(body_state,"ECAction",{"Algorithm": "ALG"})

    for terminal in Safslprocess.interface.terminals:

        if terminal.direction == "Input":
            SubElement(
                EventInputs,
                "Event",
                {
                    "name": terminal.name
                }
            )
            transition = SubElement(
                    ECC,
                    "ECTransition",
                    {
                        "Source": "START",
                        "Destination" : "BODY"
                    }
                )
            
            SubElement(
                    transition,
                    "ECEventCondition",
                    {
                        "Event": terminal.name
                    }
                )
            
        elif terminal.direction == "Output":
            SubElement(
                EventOutputs,
                "Event",
                {
                    "name": terminal.name
                }
            )
            SubElement(
                    ECC,
                    "ECTransition",
                    {
                        "Source": "BODY",
                        "Destination" : terminal.name + "_STATE"
                    }
                )
            Terminal_State = SubElement(
                    ECC,
                    "ECState",
                    {
                        "Name": terminal.name + "_STATE"
                    }
                )
            SubElement(
                    Terminal_State,
                    "ECAction",
                    {
                        "Output": terminal.name
                    }
                )
                

    for port in Safslprocess.interface.ports:
    
            if port.direction == "Input":
                SubElement(
                    InputVars,
                    "VarDeclaration",
                    {
                        "name": port.name,
                        "type" : "REAL"
                    }
                )
    
            elif port.direction == "Output":
                SubElement(
                    OutputVars,
                    "VarDeclaration",
                    {
                        "name": port.name,
                        "type":  "REAL"
                    }
                )
             
    
    for statement in Safslprocess.body.statements:
        if isinstance(statement.children[0], AssignmentNode):
            generate_assignment(statement)

        if isinstance(statement.children[0], IfNode):
            generate_if(statement)
    
    try:
        st_code = "\n".join(algorithm)
        Algorithm.text = etree.CDATA(st_code)
    except Exception as E:
        print("Error")  


    return root

def generate_assignment(statement):

    if statement.children[0].operator == "assignS":
        algorithm.append(
            f"{statement.children[0].target} := {str(statement.children[0].value.value).upper()};"
        )

    else:
        algorithm.append(
            f"{statement.target} := {statement.value};"
        )

def generate_if(statement):

    condition = generate_expression(statement.children[0].condition)

    algorithm.append(f"IF {condition} THEN")

    for stmt in statement.children[0].statements:
        generate_statement(stmt)

    algorithm.append("END_IF;")

def generate_statement(statement):

    if isinstance(statement.children[0], AssignmentNode):
        generate_assignment(statement)

    elif isinstance(statement.children[0], IfNode):
        generate_if(statement)


def generate_expression(expr):

    if isinstance(expr, Literal):
    
        if isinstance(expr.value, bool):
            return "TRUE" if expr.value else "FALSE"
        
        elif isinstance(expr, Literal):
            if isinstance(expr.value, bool):
                return "TRUE" if expr.value else "FALSE"
            return str(expr.value)

    else:
        return str(expr.value)


