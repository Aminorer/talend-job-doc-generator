"""Detailed tMap parser with structured dataclasses."""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from lxml import etree


LOGGER = logging.getLogger(__name__)


class TMapParsingError(Exception):
    """Raised when the tMap parsing fails."""


@dataclass
class TMapJoinCondition:
    """Represents a join condition applied on an input table."""

    join_type: Optional[str]
    expression: str


@dataclass
class TMapLookupProperties:
    """Lookup behaviour for an input table."""

    mode: Optional[str]
    join_model: Optional[str]
    inner_join: bool = False


@dataclass
class TMapMapping:
    """Mapping from an input (or lookup) to an output column."""

    source_table: Optional[str]
    source_column: Optional[str]
    target_table: Optional[str]
    target_column: str
    expression: Optional[str]


@dataclass
class TMapInputTable:
    """Input table configuration."""

    name: str
    lookup: Optional[TMapLookupProperties] = None
    join_conditions: List[TMapJoinCondition] = field(default_factory=list)
    mappings: List[TMapMapping] = field(default_factory=list)


@dataclass
class TMapVariable:
    """Variable (Var table) definition."""

    name: str
    expression: str
    type: Optional[str] = None
    nullable: Optional[bool] = None


@dataclass
class TMapOutputTable:
    """Output table configuration."""

    name: str
    is_reject: bool
    reject_inner_join: bool
    filters: List[str] = field(default_factory=list)
    mappings: List[TMapMapping] = field(default_factory=list)


@dataclass
class TMapParseResult:
    """Aggregated result of the tMap parsing."""

    input_tables: List[TMapInputTable] = field(default_factory=list)
    variables: List[TMapVariable] = field(default_factory=list)
    output_tables: List[TMapOutputTable] = field(default_factory=list)

    def _all_mappings(self) -> List[TMapMapping]:
        mappings: List[TMapMapping] = []
        for table in self.input_tables:
            mappings.extend(table.mappings)
        for table in self.output_tables:
            mappings.extend(table.mappings)
        return mappings

    def _all_filters(self) -> List[str]:
        filters: List[str] = []
        for table in self.output_tables:
            filters.extend(table.filters)
        return filters

    def to_dict(self) -> Dict[str, Any]:
        """Return a serialisable representation of the parse result."""
        base = asdict(self)
        base["mappings"] = [asdict(mapping) for mapping in self._all_mappings()]
        base["filters"] = self._all_filters()
        base["input_table_names"] = [table.name for table in self.input_tables]
        base["output_table_names"] = [table.name for table in self.output_tables]
        base["lookups"] = [
            {
                "table": table.name,
                "mode": table.lookup.mode if table.lookup else None,
                "join_model": table.lookup.join_model if table.lookup else None,
                "inner_join": table.lookup.inner_join if table.lookup else False,
            }
            for table in self.input_tables
            if table.lookup
        ]
        base["rejects"] = [
            table.name for table in self.output_tables if table.is_reject or table.reject_inner_join
        ]
        base["joins"] = [
            {
                "table": table.name,
                "type": join.join_type,
                "expression": join.expression,
            }
            for table in self.input_tables
            for join in table.join_conditions
        ]
        return base


class TMapParser:
    """Parse tMap XML definitions into structured dataclasses.

    Attributes:
        node: The XML node corresponding to the tMap component.
        namespaces: XML namespaces to use during XPath searches.
        logger: Logger instance for diagnostic messages.
    """

    def __init__(
        self,
        node: etree._Element,
        namespaces: Optional[Dict[str, str]] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.node = node
        self.namespaces = namespaces or {}
        self.logger = logger or LOGGER

    def parse(self) -> TMapParseResult:
        """Parse the tMap component.

        Returns:
            A populated :class:`TMapParseResult`.

        Raises:
            TMapParsingError: If the tMap content cannot be parsed.
        """
        try:
            map_element = self._get_map_element()
            input_tables = self._parse_input_tables(map_element)
            variables = self._parse_variables(map_element)
            output_tables = self._parse_output_tables(map_element)
            return TMapParseResult(
                input_tables=input_tables,
                variables=variables,
                output_tables=output_tables,
            )
        except Exception as exc:
            self.logger.exception("Échec du parsing tMap : %s", exc)
            raise TMapParsingError("Impossible d'analyser le tMap") from exc

    def _get_map_element(self) -> etree._Element:
        map_element = self.node.find(".//elementParameter[@name='MAP']", namespaces=self.namespaces)
        if map_element is None:
            raise TMapParsingError("Aucun bloc MAP trouvé dans le tMap")
        return map_element

    def _parse_input_tables(self, map_element: etree._Element) -> List[TMapInputTable]:
        tables: List[TMapInputTable] = []
        for table in map_element.findall(".//inputTables//table", namespaces=self.namespaces):
            name = table.get("name")
            if not name:
                self.logger.warning("Table d'entrée sans nom rencontrée")
                continue
            lookup = TMapLookupProperties(
                mode=table.get("lookupMode") or table.get("lookupType"),
                join_model=table.get("joinModel") or table.get("joinType"),
                inner_join=self._parse_bool(table.get("innerJoin")),
            )
            join_conditions = self._parse_join_conditions(table, lookup.join_model)
            mappings = self._parse_mapper_entries(
                table, target_table=name, default_source=name, is_output_table=False
            )
            tables.append(
                TMapInputTable(
                    name=name,
                    lookup=lookup,
                    join_conditions=join_conditions,
                    mappings=mappings,
                )
            )
        return tables

    def _parse_join_conditions(
        self, table: etree._Element, default_join_type: Optional[str]
    ) -> List[TMapJoinCondition]:
        joins: List[TMapJoinCondition] = []
        for join in table.findall(".//join", namespaces=self.namespaces):
            expression = join.get("expression") or (join.text or "").strip()
            if not expression:
                continue
            join_type = join.get("joinType") or default_join_type
            joins.append(TMapJoinCondition(join_type=join_type, expression=expression))
        return joins

    def _parse_variables(self, map_element: etree._Element) -> List[TMapVariable]:
        variables: List[TMapVariable] = []
        for entry in map_element.findall(".//varTables//varTable//mapperTableEntry", namespaces=self.namespaces):
            name = entry.get("name")
            expression = entry.get("expression")
            if not name or expression is None:
                self.logger.warning("Variable de tMap incomplète: name=%s expression=%s", name, expression)
                continue
            variables.append(
                TMapVariable(
                    name=name,
                    expression=expression,
                    type=entry.get("type"),
                    nullable=self._parse_optional_bool(entry.get("nullable")),
                )
            )
        return variables

    def _parse_output_tables(self, map_element: etree._Element) -> List[TMapOutputTable]:
        tables: List[TMapOutputTable] = []
        for table in map_element.findall(".//outputTables//table", namespaces=self.namespaces):
            name = table.get("name")
            if not name:
                self.logger.warning("Table de sortie sans nom rencontrée")
                continue
            filters = self._parse_filters(table)
            mappings = self._parse_mapper_entries(
                table, target_table=name, default_source=None, is_output_table=True
            )
            tables.append(
                TMapOutputTable(
                    name=name,
                    is_reject=self._parse_bool(table.get("isReject")),
                    reject_inner_join=self._parse_bool(table.get("rejectInnerJoin")),
                    filters=filters,
                    mappings=mappings,
                )
            )
        return tables

    def _parse_mapper_entries(
        self,
        table: etree._Element,
        target_table: Optional[str],
        default_source: Optional[str],
        is_output_table: bool,
    ) -> List[TMapMapping]:
        mappings: List[TMapMapping] = []
        for entry in table.findall(".//mapperTableEntry", namespaces=self.namespaces):
            target_column = entry.get("name")
            if not target_column:
                self.logger.warning("mapperTableEntry sans nom dans %s", target_table or "table inconnue")
                continue
            source_table = entry.get("lookup") or entry.get("input") or default_source
            source_column = entry.get("lookupColumn") or entry.get("inputColumn")
            expression = entry.get("expression")
            mapping = TMapMapping(
                source_table=source_table,
                source_column=source_column if source_column else entry.get("name") if not is_output_table else None,
                target_table=target_table,
                target_column=target_column,
                expression=expression,
            )
            mappings.append(mapping)
        return mappings

    def _parse_filters(self, table: etree._Element) -> List[str]:
        filters: List[str] = []
        for filter_condition in table.findall(".//filterCondition", namespaces=self.namespaces):
            expression = filter_condition.get("expression") or (filter_condition.text or "").strip()
            if expression:
                filters.append(expression)
        return filters

    @staticmethod
    def _parse_bool(value: Optional[str]) -> bool:
        return str(value).lower() == "true"

    @classmethod
    def _parse_optional_bool(cls, value: Optional[str]) -> Optional[bool]:
        if value is None:
            return None
        return cls._parse_bool(value)


__all__ = [
    "TMapParser",
    "TMapParseResult",
    "TMapInputTable",
    "TMapOutputTable",
    "TMapVariable",
    "TMapMapping",
    "TMapJoinCondition",
    "TMapLookupProperties",
    "TMapParsingError",
]
