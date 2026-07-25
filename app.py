'''
Created on Jul 25, 2026

@author: haris
'''

from pathlib import Path

from lark import Lark

from safsl_parser.transformer import SAFSLTransformer
from safsl_compiler.xml_writer import generate_fb_xml
from lxml import etree 


GRAMMAR_PATH = (
    Path(__file__)
    .parent
    .parent
    / "Springer_Journal\\grammar"
    / "process1.lark"
)

GENERATED_FB_PATH = (
    Path(__file__)
    .parent
    .parent
    / "Springer_Journal\\generated\\fb"
)
FilePATH = (
    Path(__file__)
    .parent
    .parent
    / "example"
    / "example1.safsl"
)

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
            xml_declaration=True

        )

if __name__ == "__main__":
    
    source  = ""
    with open("example/example1.safsl", encoding="utf-8") as f:
        source = f.read()

    
    parser = SAFSLParser()
    fb  = parser.parse(source)
  
    for process in fb.children[0].processes:
    
        xml = generate_fb_xml(process)
        pretty = pretty_xml(xml)
        with open(str(GENERATED_FB_PATH)+f"/{process.name}.xml", "wb") as file:
            file.write(pretty)