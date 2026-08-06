'''
Created on Jul 25, 2026

@author: haris
'''

from lxml.etree import Element, SubElement
from lxml import etree

from safsl_ast.nodes import AssignmentNode, IfNode, Identifier, Literal, Operation,QualifiedLiteral

from safsl_ast.nodes import ( PropertyReference,PropertyNode,SMCReference,PortNode)
algorithm = []

data_Types = { "xs:float" : "REAL" , "xs:double" : "LREAL", 
              "xs:string" : "STRING", "xs:boolean" : "BOOL", "xs:int" : "INT" 
              }

UNIT_CONVERSIONS = {
    ("QUDT:K", "QUDT:DEG_C"):
        lambda x: f"({x} - 273.15)",

    ("QUDT:DEG_C", "QUDT:K"):
        lambda x: f"({x} + 273.15)",

    ("QUDT:M3", "QUDT:L"):
        lambda x: f"({x} * 1000.0)",

    ("QUDT:L", "QUDT:M3"):
        lambda x: f"({x} / 1000.0)",

    ("QUDT:CentiM3", "QUDT:M3"):
        lambda x: f"({x} / 1000000.0)",

    ("QUDT:M3", "QUDT:CentiM3"):
        lambda x: f"({x} * 1000000.0)",

    ("QUDT:CentiM3", "QUDT:L"):
        lambda x: f"({x} / 1000.0)",

    ("QUDT:L", "QUDT:CM3"):
        lambda x: f"({x} * 1000.0)",        
    
}

reference_table = None
references = None 


def generate_fb_xml(Safslprocess,ref_table,refs):
    global reference_table
    global references
    
    reference_table = ref_table
    refs = references
    
    root = Element( "FBType", { "name": Safslprocess.name})

    interface = SubElement(root, "InterfaceList")

    EventInputs = SubElement(interface, "EventInputs")
    EventOutputs = SubElement(interface, "EventOutputs")

    InputVars = SubElement(interface, "InputVars")
    OutputVars = SubElement(interface, "OutputVars")

    BasicFB = SubElement(root, "BasicFB")
    InternalVars = SubElement(BasicFB, "InternalVars")
    
    
    for property in  Safslprocess.interface.properties:
        attributes = {
                "name": property.name,
                "type": data_Types[property.dataType],
                "initialvalue": property.value
            }
    
        SubElement(
                InternalVars,
                "VarDeclaration",
                attributes
            )
        
        reference_table[property.name] = property
        
    for range in  Safslprocess.interface.ranges:
        pass

    for port in Safslprocess.interface.ports:
        
            if port.direction == "Input":
        
                value = ""
                fbdataType = ""
                address = None
        
                if port.reference:
        
                    reference = reference_table[
                        port.reference.path[0]
                    ]
                    
                    if port.name not in reference_table:
                        reference_table[port.name] = port
                    
                    resolved = reference.resolved
    
                    if reference.submodel == "CPrp":
        
                        if reference.element_type == "Property":
                            value = reference.resolved.value
                            fbdataType = data_Types[reference.resolved.dataType]
        
                        elif reference.element_type == "Range":
                            value = f"{reference.min}:{reference.max}"
        
                    elif reference.submodel == "DEXPI":
                        
                        if resolved.element_type == "SubmodelElementCollection":
                        
                            value = resolved.value
                            address = "Empty"
                            fbdataType = data_Types[resolved.dataType]
        
        
                    else:
                        raise Exception(
                            f"Unsupported submodel {reference.submodel}"
                        )
        
        
                attributes = {
                    "name": port.name,
                    "type": fbdataType,
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
                fbdataType = ""        
                
                if port.reference:
            
                    reference = reference_table[
                        port.reference.path[0]
                    ]
            
                    if reference.submodel == "CPrp":
            
                        if reference.element_type == "Property":
                            value = reference.value
                            fbdataType = data_Types[reference.resolved.dataType]
            
                        elif reference.element_type == "Range":
                            value = f"{reference.min}:{reference.max}"
            
            
                    elif reference.submodel == "DEXPI":
            
                        # DEXPI equipment/function reference
                        value = reference.resolved.value
                        address = "Empty"
                        fbdataType = data_Types[reference.resolved.dataType]
            
            
                attributes = {
                    "name": port.name,
                    "type": fbdataType
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

def get_operand_type(expr):

    if isinstance(expr, Identifier):

        reference = reference_table.get(expr.name)

        if reference is None:
            raise Exception(
                f"Unknown identifier {expr.name}"
            )

        if isinstance(reference, PropertyNode):
            return reference.semantic_id

        elif isinstance(reference, PropertyReference):
            return reference.unit


    elif isinstance(expr, QualifiedLiteral):

        return expr.semantic_id


    elif isinstance(expr, Literal):

        return None


    raise Exception(
        f"Cannot determine semantic type of {expr}"
    )
        
    return None
    
def generate_assignment(statement):

    if statement.operator == "assignS":
        validate_semantic_expression(statement.value.expression)
        target_type = get_operand_type(statement.target)

        rhs = generate_expression(
            statement.value.expression,
            expected_type=target_type
        )

        algorithm.append(
            f"{statement.target.name} := {rhs};"
        )

    else:
        algorithm.append(
            f"{statement.target.name} := {generate_expression(statement.value.expression)};"
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


def generate_expression(expr,expected_type=None):

    if isinstance(expr, Literal):

        if isinstance(expr.value, bool):
            return "TRUE" if expr.value else "FALSE"

        return str(expr.value)

    elif isinstance(expr, QualifiedLiteral):
    
        if expected_type is None:
            return str(expr.value)
    
        if expr.semantic_id == expected_type:
            return str(expr.value)
    
        conversion = get_conversion(
            expr.semantic_id,
            expected_type
        )
    
        if conversion:
            return conversion(str(expr.value))
    
        raise Exception(
            f"No conversion from {expr.semantic_id} to {expected_type}"
        )


    elif isinstance(expr, Identifier):

        return expr.name


    elif isinstance(expr, str):

        return expr
    

    elif isinstance(expr, Operation):
        
        if expr.operator in ["lessES", "greatES", "lessS", "greatS"]:
            types = [get_expression_type(op) for op in expr.operands]
        
            if None in types:
                print("Hello")
                raise Exception(
                    f"{expr.operator} requires semantic operands"
                )
        
            target = types[0]
        
            for t in types[1:]:
                if t != target and get_conversion(t, target) is None:
                    raise Exception(
                        f"Operands are not semantically comparable: {target} and {t}"
                    )
            
            operands = [generate_expression(op) for op in expr.operands]
                
            if expr.operator == "lessES":
                return "(" + " <= ".join(operands) + ")"
        
            elif expr.operator == "greatES":
                return "(" + " >= ".join(operands) + ")"
        
            elif expr.operator == "lessS":
                return "(" + " < ".join(operands) + ")"
        
            elif expr.operator == "greatS":
                return "(" + " > ".join(operands) + ")"        
            

        elif expr.operator in ["andS", "orS"]:
        
            for operand in expr.operands:
                if get_expression_type(operand) != "BOOL":
                    raise Exception(
                        f"{expr.operator} requires BOOL operands"
                    )
        
            operands = [
                generate_expression(op)
                for op in expr.operands
            ]
        
            op = " AND " if expr.operator == "andS" else " OR "
            return "(" + op.join(operands) + ")"
        
        elif expr.operator == "notS":
        
            if get_expression_type(expr.operands[0]) != "BOOL":
                raise Exception(
                    "notS requires a BOOL operand"
                )
        
            return f"NOT ({generate_expression(expr.operands[0])})"

        
        elif expr.operator == "add":
            operands = [
                    generate_expression(op)
                    for op in expr.operands
                ]
            return "(" "+" " + ".join(operands) + ")"

        elif expr.operator == "sub":
            operands = [
                    generate_expression(op)
                    for op in expr.operands
                ]
            return "(" "-" " + ".join(operands) + ")"
            
        
        elif expr.operator == "mul":
            operands = [
                    generate_expression(op)
                    for op in expr.operands
                ]
            return "(" "*" " + ".join(operands) + ")"
        
        elif expr.operator == "div":
            operands = [
                    generate_expression(op)
                    for op in expr.operands
                ]
            return "(" "/" " + ".join(operands) + ")" 
                    
        elif expr.operator == "addS" or expr.operator == "subS":
            operands = []
    
            for operand in expr.operands:
                operand_code = generate_expression(
                    operand,
                    expected_type=expected_type
                )
    
                operand_type = get_operand_type(operand)
                if operand_type != expected_type:
                    operand_code = convert_type(
                        operand_code,
                        operand_type,
                        expected_type
                    )
                operands.append(operand_code)
            
            if expr.operator == "addS":
                return "(" + " + ".join(operands) + ")"
            else:
                return "(" + " - ".join(operands) + ")"
    
    print("Hello")
    raise Exception(f"Unknown expression type: {expr}")

def convert_type(operand_code, operand_type, expected_type):

    if operand_type == expected_type:
        return operand_code

    conversion = get_conversion(
        operand_type,
        expected_type
    )

    if conversion is None:
        raise TypeError(
            f"No conversion from {operand_type} to {expected_type}"
        )

    return conversion(operand_code)

def get_conversion(source_type, target_type):
    return UNIT_CONVERSIONS.get((source_type, target_type))

SEMANTIC_OPERATORS = {
    "addS",
    "subS",
    "mulS",
    "divS",
    "lessES",
    "greatES",
    "equal",
    "notS",
    "orS",
    "andS"
}

def validate_semantic_expression(expr):

    if isinstance(expr, Operation):

        if expr.operator in ["addS", "subS", "mulS", "divS"]:

            types = [
                get_expression_type(x)
                for x in expr.operands
            ]

            if None in types:
                raise Exception(
                    f"{expr.operator} requires semantic operands"
                )

            target = types[0]

            for t in types[1:]:

                if t != target:

                    if get_conversion(t, target) is None:
                        raise Exception(
                            f"No semantic conversion {t} -> {target}"
                        )

        for operand in expr.operands:
            validate_semantic_expression(operand)

def get_expression_type(expr):
    
    # p1, p2, etc.
    if isinstance(expr, Identifier):

        reference = reference_table.get(expr.name)


        if isinstance(reference, PropertyReference):
            return reference.unit

        if isinstance(reference, PropertyNode):
            return reference.semantic_id

        if isinstance(reference, SMCReference):
            return reference.unit
        
        if (isinstance(reference, PortNode)):
            th = get_expression_type(Identifier(name = reference.reference.path[0]))
            return get_expression_type(Identifier(name = reference.reference.path[0]))

        if reference is None:
            raise Exception(
                f"Unknown identifier {expr.name}"
            )
        

    # 10@QUDT:K
    elif isinstance(expr, QualifiedLiteral):

        return expr.semantic_id


    # 10
    elif isinstance(expr, Literal):

        return None

    elif isinstance(expr, Operation):

        if expr.operator in ["lessS", "greatS", "lessES", "greatES"]:
            return "BOOL"

        elif expr.operator in ["andS", "orS", "notS"]:
            return "BOOL"

        elif expr.operator in ["addS", "subS", "mulS", "divS"]:
            return get_expression_type(expr.operands[0])


    return None