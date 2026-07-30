'''
Created on Jul 25, 2026

@author: haris
'''

from pathlib import Path

from lark import Lark

from safsl_parser.transformer import SAFSLTransformer,AASResolver,QUDTResolver,SemanticResolver
from safsl_compiler.xml_writer import generate_fb_xml
from safsl_aas.builder import load_submodel
from lxml import etree 

GRAMMAR_PATH = (
    Path(__file__)
    .parent
    .parent
    / "SAFSL_Compiler_Tool_Chain\\grammar"
    / "process1.lark"
)

GENERATED_FB_PATH = (
    Path(__file__)
    .parent
    .parent
    / "SAFSL_Compiler_Tool_Chain\\generated\\fb"
)
FilePATH = (
    Path(__file__)
    .parent
    .parent
    / "example"
    / "example1.safsl"
)

qudt_model = {
    "http://qudt.org/vocab/quantitykind/Temperature": "DEG_C",
    "http://qudt.org/vocab/quantitykind/Pressure": "BAR",
    "http://qudt.org/vocab/quantitykind/Length": "M",
    "http://qudt.org/vocab/quantitykind/Volume": "m3"
}

class SAFSLParser:

    def __init__(self):
        self.parser = Lark.open( GRAMMAR_PATH, parser="lalr", start="start", propagate_positions=True)

    def parse(self, source:str):
        tree = self.parser.parse(source)
        transformer = SAFSLTransformer()
        ast = transformer.transform(tree)

        return ast

def pretty_xml(element):
        return etree.tostring(
            element,
            pretty_print=True,
            encoding="utf-8",
            xml_declaration=True)


def resolve_element(
        submodels,
        submodel_name,
        element_name,
        expected_type):

    if submodel_name not in submodels:
        raise Exception(
            f"Unknown submodel {submodel_name}"
        )

    submodel = submodels[submodel_name]


    if element_name not in submodel.elements:
        raise Exception(
            f"{element_name} not found in {submodel_name}"
        )


    element = submodel.elements[element_name]


    if element.element_type != expected_type:
        raise Exception(
            f"{element_name} is {element.element_type}, "
            f"expected {expected_type}"
        )


    return element

if __name__ == "__main__":

    with open("example/cstr.safsl", encoding="utf-8") as f:
        source = f.read()

    submodels = {
        "CPrp": load_submodel("submodels/CPrp.json"),
        "DEXPI": load_submodel("submodels/DEXPI.json")
    }

    parser = SAFSLParser()
    fb = parser.parse(source)

    specification = fb.children[0]

    resolver = AASResolver(
        submodels=submodels
    )

    for reference in specification.references:

        reference.resolved = resolver.resolve(
            reference
        )

    qudt_resolver = QUDTResolver(qudt_model)
    semantic_resolver = SemanticResolver()

    for reference in specification.references:
        semantic_resolver.resolve(reference)

    for reference in specification.references:

        reference.resolved = resolver.resolve(
            reference
        )    
        
        if reference.resolved and reference.resolved.semantic_id:
        
            reference.semantic_id = reference.resolved.semantic_id
        
            reference.unit = qudt_resolver.resolve_unit(
                reference.semantic_id
            )



    reference_table = {
        reference.idShort: reference
        for reference in specification.references
    }
    
    for process in specification.processes:

        xml = generate_fb_xml(
            process,
            reference_table,
            specification.references
        )

        pretty = pretty_xml(xml)

        output_file = (
            GENERATED_FB_PATH /
            f"{process.name}.xml"
        )

        with open(output_file, "wb") as file:
            file.write(pretty)
