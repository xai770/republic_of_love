#!/usr/bin/env python3
"""
LLM Task Codex Production Monitoring
====================================

Production monitoring and health checks for the LLM Task Codex system.
Provides operational visibility and alerting for production deployments.

Author: Arden (Republic of Love Engineering)
Status: Production Ready
"""

import sys
import yaml
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add framework to path
sys.path.append('/home/xai/Documents/ty_learn')
from llm_framework.blessed_qa_integration import BlessedConfigQALoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProductionMonitor:
    """
    Production monitoring for LLM Task Codex system
    Provides health checks, metrics, and operational alerts
    """
    
    def __init__(self):
        """Initialize production monitor"""
        self.workspace_root = self._find_workspace_root()
        self.blessed_configs_dir = self.workspace_root / 'output/llm_tasks'
        self.qa_loader = BlessedConfigQALoader()
        self.metrics = {}
        
    def _find_workspace_root(self) -> Path:
        """Auto-detect workspace root"""
        current = Path.cwd()
        while current.parent != current:
            if (current / 'llm_framework').exists() and (current / 'modules').exists():
                return current
            current = current.parent
        raise ValueError("ty_learn workspace root not found")
    
    def check_system_health(self) -> Dict[str, Any]:
        """
        Comprehensive system health check
        
        Returns:
            Dict containing health status and metrics
        """
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'UNKNOWN',
            'components': {},
            'metrics': {},
            'alerts': []
        }
        
        try:
            # Check blessed configs directory
            health_status['components']['blessed_configs_dir'] = self._check_blessed_configs_dir()
            
            # Check available configurations
            health_status['components']['available_configs'] = self._check_available_configs()
            
            # Check QA integration
            health_status['components']['qa_integration'] = self._check_qa_integration()
            
            # Check template system
            health_status['components']['template_system'] = self._check_template_system()
            
            # Calculate overall metrics
            health_status['metrics'] = self._calculate_metrics()
            
            # Determine overall status
            component_statuses = [comp['status'] for comp in health_status['components'].values()]
            if all(status == 'HEALTHY' for status in component_statuses):
                health_status['overall_status'] = 'HEALTHY'
            elif any(status == 'CRITICAL' for status in component_statuses):
                health_status['overall_status'] = 'CRITICAL'
            else:
                health_status['overall_status'] = 'WARNING'
                
            # Generate alerts
            health_status['alerts'] = self._generate_alerts(health_status)
            
        except Exception as e:
            health_status['overall_status'] = 'CRITICAL'
            health_status['alerts'].append({
                'level': 'CRITICAL',
                'message': f"Health check failed: {str(e)}",
                'component': 'system'
            })
            logger.error(f"Health check failed: {e}")
            
        return health_status
    
    def _check_blessed_configs_dir(self) -> Dict[str, Any]:
        """Check blessed configs directory status"""
        status = {
            'status': 'UNKNOWN',
            'exists': False,
            'readable': False,
            'writable': False,
            'file_count': 0,
            'total_size_bytes': 0
        }
        
        try:
            if self.blessed_configs_dir.exists():
                status['exists'] = True
                status['readable'] = True  # If we can check exists, we can read
                
                # Check if writable
                test_file = self.blessed_configs_dir / '.write_test'
                try:
                    test_file.touch()
                    test_file.unlink()
                    status['writable'] = True
                except:
                    status['writable'] = False
                
                # Count files and calculate size
                config_files = list(self.blessed_configs_dir.glob("*.yaml"))
                status['file_count'] = len(config_files)
                status['total_size_bytes'] = sum(f.stat().st_size for f in config_files)
                
                # Determine status
                if status['readable'] and status['writable']:
                    status['status'] = 'HEALTHY'
                elif status['readable']:
                    status['status'] = 'WARNING'
                else:
                    status['status'] = 'CRITICAL'
            else:
                status['status'] = 'CRITICAL'
                
        except Exception as e:
            status['status'] = 'CRITICAL'
            status['error'] = str(e)
            
        return status
    
    def _check_available_configs(self) -> Dict[str, Any]:
        """Check available blessed configurations"""
        status = {
            'status': 'UNKNOWN',
            'count': 0,
            'configs': [],
            'valid_configs': 0,
            'invalid_configs': 0
        }
        
        try:
            available_configs = self.qa_loader.list_available_configs()
            status['count'] = len(available_configs)
            status['configs'] = available_configs
            
            # Validate each config
            for task_id in available_configs:
                try:
                    self.qa_loader.load_blessed_config(task_id)
                    status['valid_configs'] += 1
                except:
                    status['invalid_configs'] += 1
            
            # Determine status
            if status['count'] > 0 and status['invalid_configs'] == 0:
                status['status'] = 'HEALTHY'
            elif status['count'] > 0:
                status['status'] = 'WARNING'
            else:
                status['status'] = 'CRITICAL'
                
        except Exception as e:
            status['status'] = 'CRITICAL'
            status['error'] = str(e)
            
        return status
    
    def _check_qa_integration(self) -> Dict[str, Any]:
        """Check QA system integration"""
        status = {
            'status': 'UNKNOWN',
            'compatible_configs': 0,
            'incompatible_configs': 0,
            'test_passed': False
        }
        
        try:
            available_configs = self.qa_loader.list_available_configs()
            
            for task_id in available_configs:
                try:
                    if self.qa_loader.validate_qa_compatibility(task_id):
                        status['compatible_configs'] += 1
                    else:
                        status['incompatible_configs'] += 1
                except:
                    status['incompatible_configs'] += 1
            
            # Test QA integration with first available config
            if available_configs:
                try:
                    test_task = available_configs[0]
                    qa_config = self.qa_loader.get_qa_config_for_task(test_task)
                    test_config = self.qa_loader.create_qa_test_config(test_task, "Test prompt")
                    status['test_passed'] = True
                except:
                    status['test_passed'] = False
            
            # Determine status
            if status['compatible_configs'] > 0 and status['incompatible_configs'] == 0 and status['test_passed']:
                status['status'] = 'HEALTHY'
            elif status['compatible_configs'] > 0:
                status['status'] = 'WARNING'
            else:
                status['status'] = 'CRITICAL'
                
        except Exception as e:
            status['status'] = 'CRITICAL'
            status['error'] = str(e)
            
        return status
    
    def _check_template_system(self) -> Dict[str, Any]:
        """Check V14 template system"""
        status = {
            'status': 'UNKNOWN',
            'templates_found': 0,
            'templates_readable': 0,
            'template_paths': []
        }
        
        try:
            template_dir = self.workspace_root / 'modules/ty_extract_versions/ty_extract_v14/config/templates'
            
            if template_dir.exists():
                template_files = list(template_dir.glob("*.md"))
                status['templates_found'] = len(template_files)
                status['template_paths'] = [str(f.relative_to(self.workspace_root)) for f in template_files]
                
                # Check readability
                for template_file in template_files:
                    try:
                        content = template_file.read_text()
                        if content.strip():
                            status['templates_readable'] += 1
                    except:
                        pass
                
                # Determine status
                if status['templates_found'] > 0 and status['templates_readable'] == status['templates_found']:
                    status['status'] = 'HEALTHY'
                elif status['templates_found'] > 0:
                    status['status'] = 'WARNING'
                else:
                    status['status'] = 'CRITICAL'
            else:
                status['status'] = 'CRITICAL'
                
        except Exception as e:
            status['status'] = 'CRITICAL'
            status['error'] = str(e)
            
        return status
    
    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate system metrics"""
        metrics = {
            'total_blessed_configs': 0,
            'total_storage_mb': 0.0,
            'average_config_size_kb': 0.0,
            'qa_compatibility_rate': 0.0
        }
        
        try:
            available_configs = self.qa_loader.list_available_configs()
            metrics['total_blessed_configs'] = len(available_configs)
            
            if available_configs:
                total_size = 0
                compatible_count = 0
                
                for task_id in available_configs:
                    try:
                        config_path = self.blessed_configs_dir / f"{task_id}.yaml"
                        if config_path.exists():
                            total_size += config_path.stat().st_size
                        
                        if self.qa_loader.validate_qa_compatibility(task_id):
                            compatible_count += 1
                    except:
                        pass
                
                metrics['total_storage_mb'] = total_size / (1024 * 1024)
                metrics['average_config_size_kb'] = (total_size / len(available_configs)) / 1024
                metrics['qa_compatibility_rate'] = compatible_count / len(available_configs)
                
        except Exception as e:
            logger.warning(f"Metrics calculation failed: {e}")
            
        return metrics
    
    def _generate_alerts(self, health_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate operational alerts based on health status"""
        alerts = []
        
        # Check for critical components
        for component, status in health_status['components'].items():
            if status['status'] == 'CRITICAL':
                alerts.append({
                    'level': 'CRITICAL',
                    'message': f"Component {component} is in critical state",
                    'component': component
                })
            elif status['status'] == 'WARNING':
                alerts.append({
                    'level': 'WARNING',
                    'message': f"Component {component} has warnings",
                    'component': component
                })
        
        # Check metrics thresholds
        metrics = health_status['metrics']
        
        if metrics.get('total_blessed_configs', 0) == 0:
            alerts.append({
                'level': 'CRITICAL',
                'message': "No blessed configurations found",
                'component': 'configs'
            })
        
        if metrics.get('qa_compatibility_rate', 0) < 0.8:
            alerts.append({
                'level': 'WARNING',
                'message': f"QA compatibility rate low: {metrics.get('qa_compatibility_rate', 0):.1%}",
                'component': 'qa_integration'
            })
        
        if metrics.get('total_storage_mb', 0) > 100:
            alerts.append({
                'level': 'WARNING',
                'message': f"High storage usage: {metrics.get('total_storage_mb', 0):.1f}MB",
                'component': 'storage'
            })
        
        return alerts
    
    def run_health_check(self, output_format: str = 'json') -> None:
        """
        Run complete health check and output results
        
        Args:
            output_format: Output format ('json' or 'summary')
        """
        logger.info("🏥 Starting LLM Task Codex health check...")
        
        health_status = self.check_system_health()
        
        if output_format == 'json':
            print(json.dumps(health_status, indent=2))
        else:
            self._print_health_summary(health_status)
    
    def _print_health_summary(self, health_status: Dict[str, Any]) -> None:
        """Print human-readable health summary"""
        print(f"\n🏥 LLM TASK CODEX HEALTH CHECK")
        print(f"{'=' * 50}")
        print(f"⏰ Timestamp: {health_status['timestamp']}")
        print(f"🎯 Overall Status: {health_status['overall_status']}")
        
        print(f"\n📊 COMPONENTS:")
        for component, status in health_status['components'].items():
            status_emoji = "✅" if status['status'] == 'HEALTHY' else "⚠️" if status['status'] == 'WARNING' else "❌"
            print(f"  {status_emoji} {component.replace('_', ' ').title()}: {status['status']}")
        
        print(f"\n📈 METRICS:")
        metrics = health_status['metrics']
        print(f"  📋 Blessed Configs: {metrics.get('total_blessed_configs', 0)}")
        print(f"  💾 Storage: {metrics.get('total_storage_mb', 0):.2f} MB")
        print(f"  📏 Avg Config Size: {metrics.get('average_config_size_kb', 0):.1f} KB")
        print(f"  🔍 QA Compatibility: {metrics.get('qa_compatibility_rate', 0):.1%}")
        
        alerts = health_status['alerts']
        if alerts:
            print(f"\n🚨 ALERTS ({len(alerts)}):")
            for alert in alerts:
                level_emoji = "🔴" if alert['level'] == 'CRITICAL' else "🟡"
                print(f"  {level_emoji} {alert['level']}: {alert['message']}")
        else:
            print(f"\n✅ NO ALERTS - SYSTEM HEALTHY")
        
        print(f"\n{'=' * 50}")


def main():
    """Command-line interface for production monitoring"""
    import argparse
    
    parser = argparse.ArgumentParser(description='LLM Task Codex Production Monitor')
    parser.add_argument('--format', choices=['json', 'summary'], default='summary',
                        help='Output format (default: summary)')
    
    args = parser.parse_args()
    
    try:
        monitor = ProductionMonitor()
        monitor.run_health_check(args.format)
    except Exception as e:
        logger.error(f"Monitoring failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
