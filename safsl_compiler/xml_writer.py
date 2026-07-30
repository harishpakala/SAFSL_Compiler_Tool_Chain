'''
Created on Jul 25, 2026

@author: haris
'''

from lxml.etree import Element, SubElement
from lxml import etree

from safsl_ast.nodes import AssignmentNode, IfNode, Identifier, Literal, Operation


algorithm = []

def generate_fb_xml(Safslprocess,reference_table):

    root = Element( "FBType", { "name": Safslprocess.name})

    interface = SubElement(root, "InterfaceList")

    EventInputs = SubElement(interface, "EventInputs")
    EventOutputs = SubElement(interface, "EventOutputs")

    InputVars = SubElement(interface, "InputVars")
    OutputVars = SubElement(interface, "OutputVars")

    BasicFB = SubElement(root, "BasicFB")
    InternalVars = SubElement(BasicFB, "InternalVars")
    
    
    Algorithm = SubElement( BasicFB, "Algorithm", { "Name": "ALG", "Type":"ST" })
    ECC = SubElement(root, "ECC")
    SubElement(ECC, "ECState", { "name": "START", "Initial":"true"})

    body_state = SubElement(ECC,"ECState",{"name": "BODY",})

    SubElement(body_state,"ECAction",{"Algorithm": "ALG"})
    
    
    for property in  Safslprocess.interface.properties:
        attributes = {
                "name": property.name,
                "type": "STRING",
                "initialvalue": property.value
            }
    
        SubElement(
                InternalVars,
                "VarDeclaration",
                attributes
            )
    
    for range in  Safslprocess.interface.ranges:
        pass
    
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
                    "Destination": "BODY"
                }
            )
        
            SubElement(
                transition,
                "ECEventCondition",
                {
                    "Event": terminal.name
                }
            )
        
            for predicate in Safslprocess.interface.predicates:
        
                if predicate.terminal == terminal.name:
        
                    SubElement(
                        transition,
                        "ECCondition"
                    ).text = generate_expression(
                        predicate.condition
                    )
        
                             
        elif terminal.direction == "Output":
        
            SubElement(
                EventOutputs,
                "Event",
                {
                    "name": terminal.name
                }
            )
        
            transition = SubElement(
                ECC,
                "ECTransition",
                {
                    "Source": "BODY",
                    "Destination": terminal.name + "_STATE"
                }
            )
        
            for predicate in Safslprocess.interface.predicates:
        
                if predicate.terminal == terminal.name:
        
                    SubElement(
                        transition,
                        "ECCondition"
                    ).text = generate_expression(
                        predicate.condition
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
    
            value = None
            address = None
    
            if port.reference:
    
                reference = reference_table[
                    port.reference.path[0]
                ]
    
                resolved = reference.resolved

                if reference.submodel == "CPrp":
    
                    if reference.element_type == "Property":
                        value = reference.resolved.value
    
                    elif reference.element_type == "Range":
                        value = f"{reference.min}:{reference.max}"
    
                    elif reference.submodel == "DEXPI":
                    
                        if resolved.element_type == "SubmodelElementCollection":
                    
                            value = "0.0"
                            address = "Empty"
    
    
                else:
                    raise Exception(
                        f"Unsupported submodel {reference.submodel}"
                    )
    
    
            attributes = {
                "name": port.name,
                "type": "REAL",
                "Value": value
            }
    
            if address:
                attributes["Address"] = address
    
    
            SubElement(
                InputVars,
                "VarDeclaration",
                attributes
            )
    
    
        elif port.direction == "Output":
        
            value = None
            address = None
        
            if port.reference:
        
                reference = reference_table[
                    port.reference.path[0]
                ]
        
                if reference.submodel == "CPrp":
        
                    if reference.element_type == "Property":
                        value = reference.value
        
                    elif reference.element_type == "Range":
                        value = f"{reference.min}:{reference.max}"
        
        
                elif reference.submodel == "DEXPI":
        
                    # DEXPI equipment/function reference
                    value = "0.0"
                    address = "Empty"
        
        
            attributes = {
                "name": port.name,
                "type": "REAL"
            }
        
            if value is not None:
                attributes["Value"] = value
        
            if address is not None:
                attributes["Address"] = address
        
        
            SubElement(
                OutputVars,
                "VarDeclaration",
                attributes
            )


             
    
    for statement in Safslprocess.body.statements:

        if isinstance(statement.children[0], IfNode):
            generate_if(statement)
                    
        elif isinstance(statement.children[0], AssignmentNode):
            generate_assignment(statement.children[0])


    try:
        st_code = "\n".join(algorithm)
        Algorithm.text = etree.CDATA(st_code)
    except Exception as E:
        print("Error")  


    return root

def generate_assignment(statement):

    if statement.operator == "assignS":
        algorithm.append(
            f"{statement.target} := {generate_expression(statement.value.expression)};"
        )

    else:
        algorithm.append(
            f"{statement.target} := {generate_expression(statement.value.expression)};"
        )


def generate_if(statement):
    
    condition = generate_expression(statement.children[0].condition)

    algorithm.append(f"IF {condition} THEN")

    for stmt in statement.children[0].statements:
        generate_statement(stmt)

    algorithm.append("END_IF;")

def generate_statement(statement):

    if isinstance(statement.children[0], IfNode):
        generate_if(statement)
    
    elif isinstance(statement.children[0], AssignmentNode):
        generate_assignment(statement.children[0])




def is_dexpi_signal(reference):

    return (
        reference.submodel == "DEXPI"
        and (
            reference.idShort.startswith("PIF_")
            or reference.idShort.startswith("AIF_")
        )
    )


def create_input_variable(port, reference):

    attributes = {
        "name": port.name,
        "type": "REAL"
    }


    if reference.submodel == "DEXPI":

        if is_dexpi_signal(reference):

            attributes["Value"] = "0.0"
            attributes["Address"] = "Empty"

        else:
            raise Exception(
                f"Unsupported DEXPI reference {reference.idShort}"
            )


    else:

        attributes["Value"] = reference.value

    return attributes


def generate_expression(expr):

    if isinstance(expr, Literal):

        if isinstance(expr.value, bool):
            return "TRUE" if expr.value else "FALSE"

        return str(expr.value)


    elif isinstance(expr, Identifier):

        return expr.name


    elif isinstance(expr, Operation):

        if expr.operator == "lessES":
            return (
                f"{generate_expression(expr.operands[0][0])} <= "
                f"{generate_expression(expr.operands[0][1])}"
            )

        elif expr.operator == "greatES":
            return (
                f"{generate_expression(expr.operands[0][0])} >= "
                f"{generate_expression(expr.operands[0][1])}"
            )

        elif expr.operator == "lessS":
            return (
                f"{generate_expression(expr.operands[0][0])} < "
                f"{generate_expression(expr.operands[0][1])}"
            )

        elif expr.operator == "greatS":
            return (
                f"{generate_expression(expr.operands[0][0])} > "
                f"{generate_expression(expr.operands[0][1])}"
            )
            

        elif expr.operator == "orS":
            return (
                f"({generate_expression(expr.operands[0][0])} OR "
                f"{generate_expression(expr.operands[0][1])})"
            )

        elif expr.operator == "notS":
            operand = expr.operands
        
            if isinstance(operand, list):
                operand = operand[0]
            
            return f"NOT ({generate_expression(operand)})"
            
        elif expr.operator == "add":
            return (
                f"({generate_expression(expr.operands[0])} + "
                f"{generate_expression(expr.operands[1])})"
            )

        elif expr.operator == "sub":
            return (
                f"({generate_expression(expr.operands[0])} - "
                f"{generate_expression(expr.operands[1])})"
            )
            
        
        elif expr.operator == "mul":
            return (
                f"({generate_expression(expr.operands[0])} * "
                f"{generate_expression(expr.operands[1])})"
            )
        
        elif expr.operator == "div":
            return (
                f"({generate_expression(expr.operands[0])} / "
                f"{generate_expression(expr.operands[1])})"
            )            

    raise Exception(f"Unknown expression type: {expr}")


def generate_add(
    expr,
    symbol_table,
    target_info,
    qudt_resolver
):
    return "(" + " + ".join(expr.operands) + ")"

