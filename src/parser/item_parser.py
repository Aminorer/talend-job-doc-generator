"""Parser du fichier .item Talend."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from lxml import etree
import logging

from parser.tmap_parser import TMapParser, TMapParsingError

LOGGER = logging.getLogger(__name__)


@dataclass
class TalendComponent:
    name: str
    unique_name: str
    version: Optional[str] = None
    position: Optional[Dict[str, int]] = None
    category: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    schema: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TalendConnection:
    label: Optional[str]
    connector_name: Optional[str]
    source: str
    target: str
    line_style: Optional[str] = None


class TalendItemParser:
    """Parser pour fichiers .item de Talend."""

    def __init__(self, item_path: str):
        self.item_path = Path(item_path)
        self.tree: Optional[etree._ElementTree] = None
        self.root: Optional[etree._Element] = None
        self.namespaces: Dict[str, str] = {}
        self._validate_inputs()

    def _validate_inputs(self) -> None:
        if not self.item_path.exists():
            raise FileNotFoundError(f"Le fichier {self.item_path} n'existe pas")
        if self.item_path.suffix != ".item":
            raise ValueError("Le fichier doit avoir l'extension .item")

    def parse(self) -> Dict[str, Any]:
        self._load_xml()
        self._extract_namespaces()

        job_data: Dict[str, Any] = {
            "name": self._get_job_name(),
            "version": self._get_version(),
            "job_type": self._get_job_type(),
            "default_context": self._get_attribute("defaultContext"),
            "author": self._get_attribute("author"),
            "created_at": self._get_attribute("creation"),
            "modified_at": self._get_attribute("modification"),
            "description": self._get_text_or_none("//documentation"),
            "contexts": self._parse_contexts(),
            "components": [comp.__dict__ for comp in self._parse_components()],
            "connections": [conn.__dict__ for conn in self._parse_connections()],
            "subjobs": self._parse_subjobs(),
            "notes": self._parse_notes(),
        }
        job_data["stats"] = self._calculate_stats(job_data)
        return job_data

    # --- XML helpers -----------------------------------------------------
    def _load_xml(self) -> None:
        self.tree = etree.parse(str(self.item_path))
        self.root = self.tree.getroot()

    def _extract_namespaces(self) -> None:
        assert self.root is not None
        self.namespaces = self.root.nsmap if self.root.nsmap else {}

    def _get_attribute(self, name: str) -> Optional[str]:
        assert self.root is not None
        return self.root.get(name)

    def _get_text_or_none(self, xpath: str) -> Optional[str]:
        assert self.root is not None
        if xpath.startswith("//"):
            results = self.root.xpath(xpath, namespaces=self.namespaces)
            if results:
                elem = results[0]
                if isinstance(elem, etree._Element):
                    return elem.text
                if isinstance(elem, str):
                    return elem
            return None
        elem = self.root.find(xpath, namespaces=self.namespaces)
        return elem.text if elem is not None else None

    def _local_name(self, tag: str) -> str:
        return tag.split("}")[-1] if "}" in tag else tag

    # --- Parsers ---------------------------------------------------------
    def _get_job_name(self) -> Optional[str]:
        return self._get_attribute("name") or self._get_text_or_none("//property[@name]/@name")

    def _get_version(self) -> Optional[str]:
        return self._get_attribute("version")

    def _get_job_type(self) -> Optional[str]:
        return self._get_attribute("jobType")

    def _parse_contexts(self) -> Dict[str, Dict[str, Any]]:
        assert self.root is not None
        contexts: Dict[str, Dict[str, Any]] = {}
        for context in self.root.findall(".//context", namespaces=self.namespaces):
            context_name = context.get("name", "Default")
            params: Dict[str, Dict[str, Any]] = {}
            for param in context.findall("contextParameter", namespaces=self.namespaces):
                params[param.get("name", "")] = {
                    "type": param.get("type"),
                    "value": param.get("value"),
                    "prompt": param.get("prompt"),
                    "comment": param.get("comment"),
                }
            contexts[context_name] = params
        return contexts

    def _parse_components(self) -> List[TalendComponent]:
        assert self.root is not None
        components: List[TalendComponent] = []
        for node in self.root.iter():
            if self._local_name(node.tag) != "node":
                continue
            parameters: Dict[str, Any] = {}
            unique_name = ""
            schema: List[Dict[str, Any]] = []
            for param in node.findall("elementParameter", namespaces=self.namespaces):
                name = param.get("name")
                if not name:
                    continue
                value = self._convert_parameter_value(param)
                parameters[name] = value
                if name == "UNIQUE_NAME" and isinstance(value, str):
                    unique_name = value or unique_name

            for metadata in node.findall("metadata", namespaces=self.namespaces):
                schema.extend(self._parse_schema(metadata))

            if node.get("componentName", "").lower() == "tmap":
                try:
                    parameters["tmap_details"] = TMapParser(
                        node, namespaces=self.namespaces, logger=LOGGER
                    ).parse().to_dict()
                except TMapParsingError:
                    parameters["tmap_details"] = {}

            components.append(
                TalendComponent(
                    name=node.get("componentName", "unknown"),
                    unique_name=unique_name or node.get("componentName", "unknown"),
                    version=node.get("componentVersion"),
                    position={
                        "x": int(node.get("posX", 0)),
                        "y": int(node.get("posY", 0)),
                    },
                    category=self._infer_category(node.get("componentName", "")),
                    parameters=parameters,
                    schema=schema,
                )
            )
        return components

    def _parse_connections(self) -> List[TalendConnection]:
        assert self.root is not None
        connections: List[TalendConnection] = []
        for conn in self.root.iter():
            if self._local_name(conn.tag) != "connection":
                continue
            connections.append(
                TalendConnection(
                    label=conn.get("label"),
                    connector_name=conn.get("connectorName"),
                    source=conn.get("source", ""),
                    target=conn.get("target", ""),
                    line_style=conn.get("lineStyle"),
                )
            )
        return connections

    def _parse_subjobs(self) -> List[Dict[str, Any]]:
        assert self.root is not None
        subjobs: List[Dict[str, Any]] = []
        for subjob in self.root.findall(".//subjob", namespaces=self.namespaces):
            subjobs.append({"title": subjob.get("title", ""), "start": subjob.get("start")})
        return subjobs

    def _parse_notes(self) -> List[Dict[str, Any]]:
        assert self.root is not None
        notes: List[Dict[str, Any]] = []
        for note in self.root.findall(".//note", namespaces=self.namespaces):
            notes.append(
                {
                    "label": note.get("label"),
                    "text": (note.text or "").strip(),
                    "x": int(note.get("posX", 0)),
                    "y": int(note.get("posY", 0)),
                }
            )
        return notes

    def _parse_stats(self) -> Dict[str, Any]:
        assert self.root is not None
        stats: Dict[str, Any] = {}
        parameters = self.root.find(".//parameters", namespaces=self.namespaces)
        if parameters is None:
            return stats
        for elem in parameters:
            local = self._local_name(elem.tag)
            stats[local] = elem.attrib
        return stats

    def _parse_schema(self, metadata_node: etree._Element) -> List[Dict[str, Any]]:
        schema: List[Dict[str, Any]] = []
        connector = metadata_node.get("connector") or metadata_node.get("name") or "FLOW"
        for column in metadata_node.findall("column", namespaces=self.namespaces):
            schema.append(
                {
                    "connector": connector,
                    "name": column.get("name"),
                    "type": column.get("type"),
                    "length": column.get("length"),
                    "precision": column.get("precision"),
                    "nullable": column.get("nullable"),
                    "comment": column.get("comment"),
                }
            )
        return schema

    def _convert_parameter_value(self, param: etree._Element) -> Any:
        field_type = (param.get("field") or "").upper()
        if field_type == "TABLE":
            rows: List[Dict[str, Any]] = []
            for row in param.findall(".//row", namespaces=self.namespaces):
                rows.append({k: v for k, v in row.attrib.items()})
            for el in param.findall(".//elementValue", namespaces=self.namespaces):
                rows.append({"ref": el.get("elementRef"), "value": el.get("value")})
            return rows
        if field_type in {"MEMO_SQL", "MEMO"}:
            text_value = (param.text or "").strip()
            if not text_value:
                text_value = param.get("value", "")
            lines = [text_value] if text_value else []
            for child in param:
                if child.text:
                    lines.append(child.text.strip())
            return "\n".join([line for line in lines if line])
        return param.get("value")

    def _infer_category(self, component_name: str) -> str:
        name_lower = component_name.lower()
        if "input" in name_lower:
            return "Input"
        if "output" in name_lower:
            return "Output"
        if "map" in name_lower or "filter" in name_lower or "transform" in name_lower:
            return "Transform"
        if "log" in name_lower:
            return "Log"
        return "Other"

    def _calculate_stats(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        components = job_data.get("components", [])
        connections = job_data.get("connections", [])
        contexts = job_data.get("contexts", {})

        stats = {
            "nb_components": len(components),
            "nb_connections": len(connections),
            "nb_context_vars": sum(len(c) for c in contexts.values()),
            "component_types": {},
            "connection_types": {},
        }

        for comp in components:
            name = comp.get("name")
            stats["component_types"][name] = stats["component_types"].get(name, 0) + 1

        for conn in connections:
            ctype = conn.get("connector_name")
            if ctype:
                stats["connection_types"][ctype] = stats["connection_types"].get(ctype, 0) + 1

        return stats


__all__ = ["TalendItemParser", "TalendComponent", "TalendConnection"]
