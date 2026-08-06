'''
Created on Jul 25, 2026

@author: haris
'''
'''
Created on Jun 25, 2026

@author: haris
'''
import base64
import json
import hashlib

import requests
from rdflib import Graph, Namespace, URIRef, Literal,Dataset
from rdflib.namespace import RDF, RDFS, XSD, OWL
from enum import Enum
import aas_core3_1.types as aas_types
import aas_core3_1.jsonization as aas_jsonization
from pyshacl import validate

semanticDict = {}

semanticDict["AAS"] = Namespace("https://example.org/aas/")
semanticDict["ECAD"] = Namespace("https://example.org/ecad/")
semanticDict["DEXPI"] = Namespace("https://example.org/dexpi/")
semanticDict["EX"] = Namespace("http://example.org/ex#")
semanticDict["ECLASS"] = Namespace("http://example.org/eclass#")
semanticDict["SH"] = Namespace("http://www.w3.org/ns/shacl#")
semanticDict["QUDT"] = Namespace("http://qudt.org/schema/qudt/")
semanticDict["UNIT"] = Namespace("http://qudt.org/vocab/unit/")

BASE_URI = "http://org.example.com"
GRAPHDB_ENDPOINT = "http://localhost:7200/repositories/AAS/statements"

HEADERS = {
    "Content-Type": "application/sparql-update"
}




class LiftMode(Enum):
    TEMPLATE = "T"
    INSTANCE = "I"

def validate_instance(data_graph: Graph, shacl_graph: Graph):
    conforms, report_graph, report_text = validate(
        data_graph=data_graph,
        shacl_graph=shacl_graph,
        inference='rdfs',
        debug=False
    )

    if not conforms:
        raise ValueError("SHACL validation failed:\n" + str(report_text))

    return True

def push_to_graphdb(triples,submodel_id):
    a = compute_uri(submodel_id)
    graph_uri = URIRef(a)
        
    g = Graph()
    for t in triples:
        g.add(t)

    sparql_data = g.serialize(format="nt")

    query = f"""
    INSERT DATA {{
            GRAPH <{a}> {{
                {sparql_data}
            }}
    }}
    """

    response = requests.post(
        GRAPHDB_ENDPOINT,
        data=query.encode("utf-8"),
        headers=HEADERS
    )

    if response.status_code not in [200, 204]:
        print(response.text)
        raise Exception("Failed to insert into GraphDB")

    print("Data pushed to GraphDB")

def map_xsd_datatype(value_type):
    mapping = {
        "string": XSD.string,
        "boolean": XSD.boolean,
        "int": XSD.integer,
        "integer": XSD.integer,
        "float": XSD.float,
        "double": XSD.double,
        "decimal": XSD.decimal,
    }

    return XSD.string#mapping.get(value_type.lower(), XSD.string)

def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def b64(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("utf-8").rstrip("=")


def predicate_from_idshort(id_short:str):
    return URIRef(BASE_URI +"/has" +id_short[0].upper()+id_short[1:])

def predicate_for_relation(id_short:str):
    return URIRef(BASE_URI +"/"+id_short)

def getOntoConcept(element):
    if (element.qualifiers):
        for qual in element.qualifiers:
            if qual.type == "ontoConcept":
                return qual.value
    
    return None

def compute_uri(submodel_id: str, path: str = "") -> URIRef:
    """
    Algorithm 3: URI computing the UR
    """

    sub_hash = b64(submodel_id)

    # empty path for root element
    path_hash = b64(path if path else "")

    uri = f"{BASE_URI}/{sub_hash}/{path_hash}"

    return URIRef(uri)

def template_lifting(submodelT : aas_types.Submodel, graph : Graph):
    """
    Algorithm 1 : Lifting the Template 
    """ 
    # --- R1: root template node ---
    
    t_node = compute_uri(submodelT.id, "")
    t_shape = compute_uri(submodelT.id, "shape")

    graph.add((t_node, RDF.type, OWL.Class))
    graph.add((t_shape, RDF.type, semanticDict["SH"].NodeShape))
    graph.add((t_shape, semanticDict["SH"].targetClass, t_node))
    graph.add((t_node, RDFS.label, Literal(submodelT.id_short)))
    
    lift_elements(graph,submodelT.id,submodelT.submodel_elements,LiftMode.TEMPLATE,"",t_shape)
    
def instance_lifting(submodelI, graph: Graph, shacl_graph: Graph,domain):

   # C_T = compute_uri(submodelI.id, "")

    a = compute_uri(submodelI.id)#, "/instance")

    #graph.add((a, RDF.type, C_T))
    graph.add((a, RDF.type, semanticDict["AAS"].SubmodelInstance))
    graph.add((a, RDFS.label, Literal(submodelI.id_short)))

    lift_elements(
        graph,
        submodelI.id,
        submodelI.submodel_elements,
        LiftMode.INSTANCE,
        "",
        domain,
        None
    )
    
def lift_elements(graph : Graph,
                  submodel_Id : str,
                  submodelElements : [aas_types.SubmodelElement],
                  _type :str,
                  path,
                  domain,
                  shape):
    
    for element in submodelElements:
        if type(element) == aas_types.Property:
            lift_Property(graph, submodel_Id, element, _type,path,shape)
        if type(element) == aas_types.Range:
            lift_Range(graph, submodel_Id, element, _type,path,shape)
        if type(element) == aas_types.SubmodelElementCollection:
            lift_SMC(graph, submodel_Id, element, _type,path,domain,shape) 
        if type(element) == aas_types.RelationshipElement:
            lift_RelationshipElement(graph,submodel_Id,element,_type,path,shape)
    
def lift_SMC(graph: Graph,
             submodel_Id: str,
             smcElement: aas_types.SubmodelElementCollection,
             _type: LiftMode,
             parent_path: str,
             domain,
             shape):
    """
    Rule R5 : Lifting the Submodel Element Collection
    """

    # --- path construction ---
    if parent_path:
        path = parent_path + "." + smcElement.id_short
    else:
        path = smcElement.id_short

    smc_uri = compute_uri(submodel_Id, path)

    if _type == LiftMode.TEMPLATE:

        # OWL object property (SMC as structural relation)
        graph.add((smc_uri, RDF.type, OWL.ObjectProperty))
        graph.add((smc_uri, RDFS.label, Literal(smcElement.id_short)))
        
        shape_node = compute_uri(submodel_Id, path + "/shape")
        # SHACL NodeShape
        graph.add((shape_node, RDF.type, semanticDict["SH"].NodeShape))
        graph.add((shape_node, semanticDict["SH"].path, smc_uri))
        graph.add((shape_node, semanticDict["SH"].class_, semanticDict["AAS"].SMC))
        graph.add((shape_node, semanticDict["SH"].minCount, Literal(1)))

        # recurse into children
        lift_elements(
            graph,
            submodel_Id,
            smcElement.value,
            _type,
            path,
            shape_node
        )

        # attach to parent shape
        if shape is not None:
            graph.add((shape, semanticDict["SH"].property, shape_node))

    elif _type == LiftMode.INSTANCE:
        ontoConcept = getOntoConcept(smcElement)
        
        if ontoConcept is not None:
            pass
        
        parent_node = compute_uri(submodel_Id, parent_path)

        smc_instance = compute_uri(submodel_Id, path)# + ".sm")

        # (a, P_c, I_c)
        #graph.add((parent_node, smc_uri, smc_instance))

        # I_c type
        graph.add((smc_instance, RDF.type, semanticDict["AAS"].SMC))
        
        
        if ontoConcept is not None:
            gOntoConcept = URIRef(domain+":"+ontoConcept)
            if (gOntoConcept, RDF.type, semanticDict["AAS"].SMC) not in graph :
                graph.add((gOntoConcept, RDF.type, semanticDict["AAS"].SMC))
                graph.add((gOntoConcept, RDFS.label, Literal(ontoConcept)))  

            #graph.add((gOntoConcept, RDF.type, semanticDict["AAS"].SMC))            
            predicate = predicate_from_idshort(ontoConcept)
            graph.add((smc_uri, RDF.type , gOntoConcept))

        else:
            predicate = predicate_from_idshort(smcElement.id_short[0].upper()+smcElement.id_short[1:])
        
        graph.add((smc_uri, RDFS.label, Literal(smcElement.id_short)))
        graph.add((parent_node, predicate , smc_uri))
        
        
        # recurse into children
        lift_elements(
            graph,
            submodel_Id,
            smcElement.value,
            _type,
            path,
            domain,
            None
        )

    lift_SemanticId(graph, submodel_Id, smcElement, path)
  
def lift_Property(
        graph: Graph,
        submodel_Id: str,
        propertyElement: aas_types.Property,
        _type: str,
        parent_path: str,
        shape=None):

    """
    Rule R3 : Lifting the Property Element
    """

    if parent_path:
        path = parent_path + "." + propertyElement.id_short
    else:
        path = propertyElement.id_short

    property_uri = compute_uri(submodel_Id, path)

    if _type == LiftMode.TEMPLATE:

        shape_node = compute_uri(submodel_Id, path + "/shape")

        # OWL schema element
        graph.add((property_uri, RDF.type, OWL.DatatypeProperty))
        graph.add((property_uri, RDFS.label, Literal(propertyElement.id_short)))

        # SHACL constraint
        graph.add((shape_node, RDF.type, semanticDict["SH"].PropertyShape))
        graph.add((shape_node, semanticDict["SH"].path, property_uri))
        graph.add((shape_node, semanticDict["SH"].minCount, Literal(1)))

        graph.add((
                shape_node,
                semanticDict["SH"].datatype,
                map_xsd_datatype(propertyElement.value_type)))

        if shape is not None:
            graph.add((shape, semanticDict["SH"].property, shape_node))
        


    elif _type == LiftMode.INSTANCE:
        ontoConcept = getOntoConcept(propertyElement)
        parent_node = compute_uri(submodel_Id, parent_path)

        value = Literal(
            propertyElement.value,
            datatype=map_xsd_datatype(propertyElement.value_type)
        )
        
        predicate = predicate_from_idshort(propertyElement.id_short)
        #graph.add((parent_node, property_uri, value))
        
        graph.add((parent_node, predicate , value))
        
    #lift_SemanticId(graph, submodel_Id, propertyElement, path)
           
def lift_Range(graph: Graph,
               submodel_Id: str,
               rangeElement: aas_types.Range,
               _type: LiftMode,
               parent_path: str,
               shape=None):
    """
    Rule R4 : Lifting the Range Element
    """

    # --- build hierarchical path ---
    if parent_path:
        path = parent_path + "." + rangeElement.id_short
    else:
        path = rangeElement.id_short

    property_uri = compute_uri(submodel_Id, path)

    if _type == LiftMode.TEMPLATE:

        shape_node = compute_uri(submodel_Id, path + "/shape")

        # define Interval class once (idempotent)
        if (semanticDict["AAS"].Interval, RDF.type, OWL.Class) not in graph:
            graph.add((semanticDict["AAS"].Interval, RDF.type, OWL.Class))
            graph.add((semanticDict["AAS"].Interval, RDFS.label, Literal("Interval")))

        # OWL object property
        graph.add((property_uri, RDF.type, OWL.ObjectProperty))
        graph.add((property_uri, RDFS.label, Literal(rangeElement.id_short)))

        # SHACL constraint
        graph.add((shape_node, RDF.type, semanticDict["SH"].PropertyShape))
        graph.add((shape_node, semanticDict["SH"].path, property_uri))
        graph.add((shape_node, semanticDict["SH"].class_, semanticDict["AAS"].Interval))
        graph.add((shape_node, semanticDict["SH"].minCount, Literal(1)))

        if shape is not None:
            graph.add((shape, semanticDict["SH"].property, shape_node))

    elif _type == LiftMode.INSTANCE:
        ontoConcept = getOntoConcept(rangeElement)
        parent_node = compute_uri(submodel_Id, parent_path)

        interval_node = compute_uri(submodel_Id, path + ".interval")

        # (a, P_r, I_r)
        graph.add((parent_node, property_uri, interval_node))

        # I_r type
        graph.add((interval_node, RDF.type, semanticDict["AAS"].Interval))

        # min value
        if hasattr(rangeElement, "min") and rangeElement.min is not None:
            graph.add((
                interval_node,
                semanticDict["AAS"].min,
                Literal(
                    rangeElement.min,
                    datatype=map_xsd_datatype(rangeElement.value_type)
                )
            ))

        # max value
        if hasattr(rangeElement, "max") and rangeElement.max is not None:
            graph.add((
                interval_node,
                semanticDict["AAS"].max,
                Literal(
                    rangeElement.max,
                    datatype=map_xsd_datatype(rangeElement.value_type)
                )
            ))

    lift_SemanticId(graph, submodel_Id, rangeElement, path)
    
def lift_RelationshipElement(
        graph: Graph,
        submodel_Id: str,
        relationshipElement: aas_types.RelationshipElement,
        _type: LiftMode,
        parent_path: str,
        shape=None):

    """
    Rule R6 : Lifting the RelationshipElement
    """

    if parent_path:
        path = parent_path + "." + relationshipElement.id_short
    else:
        path = relationshipElement.id_short

    rel_uri = ""#AAS[relationshipElement.id_short]

    if _type == LiftMode.TEMPLATE:

        # Create ontology term only if missing
        if (rel_uri, RDF.type, OWL.ObjectProperty) not in graph:
            graph.add((rel_uri, RDF.type, OWL.ObjectProperty))
            graph.add((rel_uri, RDFS.label, Literal(relationshipElement.id_short)))

        # SHACL shape for validation
        shape_node = compute_uri(submodel_Id, path + "/shape")

        graph.add((shape_node, RDF.type, semanticDict["SH"].PropertyShape))
        graph.add((shape_node, semanticDict["SH"].path, rel_uri))

        # relationship should link AAS elements
        graph.add((shape_node, semanticDict["SH"].class_, semanticDict["SH"].SubmodelElement))

        if shape is not None:
            graph.add((shape, semanticDict["SH"].property, shape_node))

    elif _type == LiftMode.INSTANCE:
        first_keys = relationshipElement.first.keys
        first_submodel = first_keys[0].value
        first_path = ".".join(k.value for k in first_keys[1:])
        first_uri = compute_uri(first_submodel, first_path)

        second_keys = relationshipElement.second.keys
        second_submodel = second_keys[0].value
        second_path = ".".join(k.value for k in second_keys[1:])
        second_uri = compute_uri(second_submodel, second_path)
        
        relationPredicate = predicate_for_relation(relationshipElement.id_short)
        
        graph.add((first_uri, relationPredicate, second_uri))

    lift_SemanticId(graph, submodel_Id, relationshipElement, path)    

def resolve_semantic_id(uri: URIRef) -> str:
    """
    Resolve a SemanticId to one of the R7 modes.
    """
    uri = str(uri)

    if uri.startswith("http://qudt.org/vocab/unit/"):
        return "unit"

    if uri.startswith("http://qudt.org/vocab/quantitykind/"):
        return "quantitykind"

    if uri.startswith("https://eclass.eu/"):
        return "classification"

    return "annotation"

def lift_SemanticId(
    graph: Graph,
    submodel_id: str,
    element: aas_types.SubmodelElement,
    parent_path: str,
    ) -> None:
    """
    Rule R7 : SemanticId enrichment
    """
    if parent_path:
        path = parent_path + "." + element.id_short
    else:
        path = element.id_short

    e_node = compute_uri(submodel_id, path)

    if element.semantic_id is None:
        return

    if len(element.semantic_id.keys) == 0:
        return

    semantic_uri = URIRef(element.semantic_id.keys[-1].value)

    mode = resolve_semantic_id(semantic_uri)

    if mode == "unit":
        graph.add((e_node, semanticDict["QUDT"].hasUnit, semantic_uri))

    elif mode == "quantitykind":
        graph.add((e_node, semanticDict["QUDT"].hasQuantityKind, semantic_uri))

    elif mode == "classification":
        graph.add((e_node, RDF.type, semantic_uri))

    else:
        graph.add((e_node, RDFS.seeAlso, semantic_uri))

def lift_aas(aasSubmodel : aas_types.Submodel,
             _type : LiftMode,file_name,domain):
    
    ds = Dataset()
    a = compute_uri(aasSubmodel.id)
    graph_uri = URIRef(a)

    graph = ds.graph(graph_uri)
    aasSM = URIRef("aas:smc")
    graph.bind("aas", semanticDict["AAS"])
    graph.bind("ex", semanticDict["EX"])
    graph.bind(domain, semanticDict[domain.upper()])
    graph.bind("qudt", semanticDict["QUDT"])
    graph.bind("unit", semanticDict["UNIT"])
    interval = URIRef("aas:Interval")
    
    if (interval, RDF.type, OWL.Class) not in graph :
        graph.add((interval, RDF.type, OWL.Class))
        graph.add((interval, RDFS.label, Literal("Interval")))

    
    
    if (aasSM, RDF.type, OWL.Class) not in graph:
        graph.add((interval, RDF.type, OWL.Class))
        graph.add((interval, RDFS.label, Literal("smc")))
    

    elif file_name == "sample_dexpi.json":
        pass
        
        
    instance_lifting(aasSubmodel, graph, _type,domain)

    return graph


if __name__ == "__main__":
    
    file_dict = {"ecad":"sample_ecad.json","dexpi":"sample_dexpi.json"}
    
    for domain,filename in file_dict.items():
        with open(filename, "r") as f:
            model = json.load(f)
        
        _type = LiftMode.INSTANCE
        
        submodel1 = aas_jsonization.submodel_from_jsonable(
            model
        )
    
        graph = lift_aas(submodel1,_type,filename,domain)
        push_to_graphdb(graph,submodel1.id)