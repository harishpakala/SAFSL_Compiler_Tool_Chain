'''
Created on Jul 25, 2026

@author: haris
'''
import json

from safsl_ast.nodes import (
    PropertyReference,
    SubmodelReference,
    RangeReference,
    SMCReference
    
)
def load_submodel(path):

    with open(path, encoding="utf-8") as f:
        data = json.load(f)


    submodel = SubmodelReference(
        name=data["idShort"],
        identifier=data["id"]
    )


    for element in data["submodelElements"]:

        reference = parse_element(
            submodel.name,
            element
        )

        submodel.elements[
            reference.idShort
        ] = reference


    return { data["idShort"] : submodel}

def extract_semantic_id(element):

    try:
        semantic = element.get("semanticId")

        if not semantic:
            return None
    
        keys = semantic.get("keys")
    
        if not keys:
            return None
    
        return keys[0]["value"]
    
    except Exception as E:
        return None


def parse_element(submodel_name, element, path=None):

    if path is None:
        path = []

    element_type = element["modelType"]["name"]

    current_path = path + [element["idShort"]]


    if element_type == "Property":
        
        semantic_id = extract_semantic_id(element)

        return PropertyReference(
            idShort=element["idShort"],
            submodel=submodel_name,
            path=current_path,
            dataType=element["valueType"],
            value=element.get("value"),
            semantic_id=semantic_id
        )


    elif element_type == "Range":

        return RangeReference(
            idShort=element["idShort"],
            submodel=submodel_name,
            path=current_path,
            min=element.get("min"),
            max=element.get("max")
        )

    elif element_type == "SubmodelElementCollection":
    
        smc = SMCReference(
            idShort=element["idShort"],
            submodel=submodel_name,
            path=current_path
        )
    
        for child in element.get("value", []):
    
            child_ref = parse_element(
                submodel_name,
                child,
                current_path
            )
    
            smc.elements[child_ref.idShort] = child_ref
    
        return smc

    else:

        raise Exception(
            f"Unsupported AAS element {element_type}"
        )


def parse_smc(submodel_name, element):

    smc = SMCReference(
        idShort=element["idShort"],
        submodel=submodel_name,
        target=element["idShort"]
    )


    for child in element.get("value", []):

        child_ref = parse_element(
            submodel_name,
            child
        )

        smc.elements[
            child_ref.idShort
        ] = child_ref


    return smc
