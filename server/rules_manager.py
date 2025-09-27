"""
User-defined rules management system with persistence.
"""
import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Rules configuration file
RULES_FILE = Path("config/rules.json")


class RulesManager:
    """Manage user-defined rules with persistence."""
    
    def __init__(self):
        self.rules: List[Dict[str, Any]] = []
        self.load_rules()
    
    def load_rules(self) -> None:
        """Load rules from the configuration file."""
        try:
            if RULES_FILE.exists():
                with open(RULES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.rules = data.get('rules', [])
                    logger.info(f"Loaded {len(self.rules)} rules from {RULES_FILE}")
            else:
                logger.info("No rules file found, starting with empty rules")
                self.rules = []
        except Exception as e:
            logger.error(f"Error loading rules: {e}")
            self.rules = []
    
    def save_rules(self) -> bool:
        """Save rules to the configuration file."""
        try:
            # Ensure config directory exists
            RULES_FILE.parent.mkdir(exist_ok=True)
            
            data = {
                "version": 1,
                "rules": self.rules
            }
            
            with open(RULES_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self.rules)} rules to {RULES_FILE}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving rules: {e}")
            return False
    
    def add_rule(self, rule_text: str, category: str = "general", priority: int = 1) -> Dict[str, Any]:
        """
        Add a new rule.
        
        Args:
            rule_text: The rule description
            category: Rule category (e.g., 'visualization', 'analysis', 'general')
            priority: Rule priority (1-10, higher = more important)
            
        Returns:
            The created rule dictionary
        """
        rule = {
            "id": len(self.rules) + 1,
            "text": rule_text.strip(),
            "category": category,
            "priority": priority,
            "active": True,
            "created_at": self._get_timestamp()
        }
        
        self.rules.append(rule)
        self.save_rules()
        
        logger.info(f"Added rule: {rule_text[:50]}...")
        return rule
    
    def update_rule(self, rule_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Update an existing rule.
        
        Args:
            rule_id: ID of the rule to update
            **kwargs: Fields to update
            
        Returns:
            Updated rule or None if not found
        """
        for rule in self.rules:
            if rule["id"] == rule_id:
                for key, value in kwargs.items():
                    if key in ["text", "category", "priority", "active"]:
                        rule[key] = value
                
                rule["updated_at"] = self._get_timestamp()
                self.save_rules()
                
                logger.info(f"Updated rule {rule_id}")
                return rule
        
        return None
    
    def delete_rule(self, rule_id: int) -> bool:
        """
        Delete a rule.
        
        Args:
            rule_id: ID of the rule to delete
            
        Returns:
            True if deleted, False if not found
        """
        for i, rule in enumerate(self.rules):
            if rule["id"] == rule_id:
                deleted_rule = self.rules.pop(i)
                self.save_rules()
                
                logger.info(f"Deleted rule {rule_id}: {deleted_rule['text'][:50]}...")
                return True
        
        return False
    
    def get_rules(self, category: Optional[str] = None, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get rules, optionally filtered by category.
        
        Args:
            category: Filter by category (None for all)
            active_only: Only return active rules
            
        Returns:
            List of rules
        """
        filtered_rules = self.rules
        
        if active_only:
            filtered_rules = [r for r in filtered_rules if r.get("active", True)]
        
        if category:
            filtered_rules = [r for r in filtered_rules if r.get("category") == category]
        
        # Sort by priority (descending) then by creation date
        return sorted(filtered_rules, key=lambda r: (-r.get("priority", 1), r.get("created_at", "")))
    
    def get_rules_text(self, category: Optional[str] = None) -> List[str]:
        """
        Get rule texts as a list of strings.
        
        Args:
            category: Filter by category (None for all)
            
        Returns:
            List of rule texts
        """
        rules = self.get_rules(category=category, active_only=True)
        return [rule["text"] for rule in rules]
    
    def get_rule_by_id(self, rule_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific rule by ID."""
        for rule in self.rules:
            if rule["id"] == rule_id:
                return rule
        return None
    
    def clear_rules(self, category: Optional[str] = None) -> int:
        """
        Clear rules, optionally by category.
        
        Args:
            category: Category to clear (None for all)
            
        Returns:
            Number of rules cleared
        """
        if category:
            original_count = len(self.rules)
            self.rules = [r for r in self.rules if r.get("category") != category]
            cleared_count = original_count - len(self.rules)
        else:
            cleared_count = len(self.rules)
            self.rules = []
        
        self.save_rules()
        logger.info(f"Cleared {cleared_count} rules")
        return cleared_count
    
    def get_categories(self) -> List[str]:
        """Get all unique rule categories."""
        categories = set()
        for rule in self.rules:
            categories.add(rule.get("category", "general"))
        return sorted(list(categories))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the rules."""
        active_rules = [r for r in self.rules if r.get("active", True)]
        categories = self.get_categories()
        
        category_counts = {}
        for category in categories:
            category_counts[category] = len([r for r in active_rules if r.get("category") == category])
        
        return {
            "total_rules": len(self.rules),
            "active_rules": len(active_rules),
            "categories": categories,
            "category_counts": category_counts
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp as ISO string."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def import_rules_from_text(self, rules_text: str, category: str = "imported") -> int:
        """
        Import rules from a text block (one rule per line).
        
        Args:
            rules_text: Text containing rules (one per line)
            category: Category for imported rules
            
        Returns:
            Number of rules imported
        """
        lines = [line.strip() for line in rules_text.split('\n') if line.strip()]
        imported_count = 0
        
        for line in lines:
            if line and not line.startswith('#'):  # Skip comments
                self.add_rule(line, category=category)
                imported_count += 1
        
        logger.info(f"Imported {imported_count} rules")
        return imported_count


# Global rules manager instance
rules_manager = RulesManager()


# Predefined example rules for different categories
EXAMPLE_RULES = {
    "visualization": [
        "All plots should use a professional color scheme with high contrast",
        "Charts should include proper titles, axis labels, and legends",
        "Use consistent font families across all visualizations",
        "Include data source information in chart subtitles",
        "Ensure plots are accessible with colorblind-friendly palettes"
    ],
    "analysis": [
        "Always check for missing values and outliers before analysis",
        "Provide statistical significance tests when comparing groups",
        "Include confidence intervals for estimates",
        "Document assumptions made during analysis",
        "Validate results with multiple approaches when possible"
    ],
    "formatting": [
        "Use consistent decimal places for similar metrics",
        "Format currency values with appropriate symbols and commas",
        "Round percentages to one decimal place unless precision is critical",
        "Use scientific notation for very large or small numbers",
        "Include units of measurement in all numeric displays"
    ]
}
