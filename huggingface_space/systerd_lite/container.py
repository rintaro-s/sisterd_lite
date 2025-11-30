#!/usr/bin/env python3
"""
Docker container management for isolated Python execution.
Provides container creation, management, and code execution capabilities.
"""

import asyncio
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContainerManager:
    """Manage Docker containers for isolated Python execution"""
    
    def __init__(self):
        self.containers: Dict[str, Dict[str, Any]] = {}
        self._check_docker()
    
    def _check_docker(self) -> bool:
        """Check if Docker is available"""
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("Docker not available")
            return False
    
    def create_python_container(self, name: str, python_version: str = "3.11",
                               packages: List[str] = None,
                               persistent: bool = False) -> Dict[str, Any]:
        """
        Create a Python container for isolated execution.
        
        Args:
            name: Container name
            python_version: Python version (3.9, 3.10, 3.11, 3.12)
            packages: List of pip packages to install
            persistent: Keep container running after creation
        """
        try:
            # Generate unique container name
            container_name = f"systerd-python-{name}"
            
            # Prepare Dockerfile
            dockerfile = self._generate_dockerfile(python_version, packages or [])
            
            # Create temporary directory for build context
            with tempfile.TemporaryDirectory() as tmpdir:
                tmppath = Path(tmpdir)
                dockerfile_path = tmppath / 'Dockerfile'
                dockerfile_path.write_text(dockerfile)
                
                # Build image
                image_name = f"systerd-python:{name}"
                build_cmd = [
                    'docker', 'build',
                    '-t', image_name,
                    '-f', str(dockerfile_path),
                    str(tmppath)
                ]
                
                result = subprocess.run(
                    build_cmd,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode != 0:
                    return {
                        'status': 'error',
                        'error': f'Build failed: {result.stderr}'
                    }
            
            # Run container
            run_cmd = [
                'docker', 'run',
                '--name', container_name,
                '-d' if persistent else '--rm',
                '--memory', '512m',
                '--cpus', '1',
                '--network', 'none',  # Isolated by default
            ]
            
            if persistent:
                run_cmd.extend([
                    '-i',  # Keep STDIN open
                    image_name,
                    'sleep', 'infinity'
                ])
            else:
                run_cmd.extend([image_name, 'python', '-c', 'print("Container ready")'])
            
            result = subprocess.run(
                run_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return {
                    'status': 'error',
                    'error': f'Container start failed: {result.stderr}'
                }
            
            container_id = result.stdout.strip()
            
            # Store container info
            self.containers[name] = {
                'name': container_name,
                'container_id': container_id,
                'image': image_name,
                'python_version': python_version,
                'packages': packages or [],
                'persistent': persistent,
                'status': 'running' if persistent else 'exited'
            }
            
            return {
                'status': 'ok',
                'container_name': container_name,
                'container_id': container_id,
                'image': image_name,
                'python_version': python_version,
                'packages': packages or []
            }
        
        except subprocess.TimeoutExpired:
            return {
                'status': 'error',
                'error': 'Container creation timed out'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _generate_dockerfile(self, python_version: str, packages: List[str]) -> str:
        """Generate Dockerfile for Python container"""
        dockerfile = f"""FROM python:{python_version}-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \\
    pip --upgrade
"""
        
        if packages:
            packages_str = ' \\\n    '.join(packages)
            dockerfile += f"""
RUN pip install --no-cache-dir \\
    {packages_str}
"""
        
        dockerfile += """
# Set working directory
WORKDIR /workspace

# Default command
CMD ["python"]
"""
        
        return dockerfile
    
    def execute_code(self, container_name: str, code: str,
                    timeout: int = 30) -> Dict[str, Any]:
        """
        Execute Python code in a container.
        
        Args:
            container_name: Name of the container (without systerd-python- prefix)
            code: Python code to execute
            timeout: Execution timeout in seconds
        """
        try:
            full_name = f"systerd-python-{container_name}"
            
            # Check if container exists
            if container_name not in self.containers:
                return {
                    'status': 'error',
                    'error': f'Container {container_name} not found'
                }
            
            container_info = self.containers[container_name]
            
            # Create temporary file with code
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                code_file = f.name
            
            try:
                # Copy code to container
                subprocess.run(
                    ['docker', 'cp', code_file, f'{full_name}:/tmp/code.py'],
                    check=True,
                    capture_output=True,
                    timeout=5
                )
                
                # Execute code
                result = subprocess.run(
                    ['docker', 'exec', full_name, 'python', '/tmp/code.py'],
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                return {
                    'status': 'ok',
                    'container': container_name,
                    'exit_code': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'success': result.returncode == 0
                }
            
            finally:
                # Clean up temp file
                Path(code_file).unlink(missing_ok=True)
        
        except subprocess.TimeoutExpired:
            return {
                'status': 'error',
                'error': f'Execution timed out after {timeout}s'
            }
        except subprocess.CalledProcessError as e:
            return {
                'status': 'error',
                'error': f'Docker command failed: {e.stderr}'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def execute_script(self, container_name: str, script_path: str,
                      args: List[str] = None, timeout: int = 30) -> Dict[str, Any]:
        """Execute a Python script file in container"""
        try:
            with open(script_path, 'r') as f:
                code = f.read()
            
            return self.execute_code(container_name, code, timeout)
        
        except FileNotFoundError:
            return {
                'status': 'error',
                'error': f'Script not found: {script_path}'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def list_containers(self) -> List[Dict[str, Any]]:
        """List all managed containers"""
        containers = []
        
        for name, info in self.containers.items():
            # Get current status from Docker
            try:
                result = subprocess.run(
                    ['docker', 'inspect', info['name'], '--format', '{{.State.Status}}'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    info['status'] = result.stdout.strip()
                else:
                    info['status'] = 'not_found'
            except:
                info['status'] = 'unknown'
            
            containers.append({
                'name': name,
                **info
            })
        
        return containers
    
    def stop_container(self, container_name: str) -> Dict[str, Any]:
        """Stop a running container"""
        try:
            full_name = f"systerd-python-{container_name}"
            
            result = subprocess.run(
                ['docker', 'stop', full_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return {
                    'status': 'error',
                    'error': result.stderr
                }
            
            if container_name in self.containers:
                self.containers[container_name]['status'] = 'stopped'
            
            return {
                'status': 'ok',
                'message': f'Container {container_name} stopped'
            }
        
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def remove_container(self, container_name: str) -> Dict[str, Any]:
        """Remove a container"""
        try:
            full_name = f"systerd-python-{container_name}"
            
            # Stop first
            subprocess.run(
                ['docker', 'stop', full_name],
                capture_output=True,
                timeout=10
            )
            
            # Remove
            result = subprocess.run(
                ['docker', 'rm', full_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    'status': 'error',
                    'error': result.stderr
                }
            
            # Remove from tracking
            if container_name in self.containers:
                del self.containers[container_name]
            
            return {
                'status': 'ok',
                'message': f'Container {container_name} removed'
            }
        
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def install_packages(self, container_name: str,
                        packages: List[str]) -> Dict[str, Any]:
        """Install additional packages in a running container"""
        try:
            full_name = f"systerd-python-{container_name}"
            
            if container_name not in self.containers:
                return {
                    'status': 'error',
                    'error': f'Container {container_name} not found'
                }
            
            packages_str = ' '.join(packages)
            
            result = subprocess.run(
                ['docker', 'exec', full_name, 'pip', 'install'] + packages,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                return {
                    'status': 'error',
                    'error': result.stderr
                }
            
            # Update tracked packages
            self.containers[container_name]['packages'].extend(packages)
            
            return {
                'status': 'ok',
                'packages': packages,
                'output': result.stdout
            }
        
        except subprocess.TimeoutExpired:
            return {
                'status': 'error',
                'error': 'Package installation timed out'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_container_info(self, container_name: str) -> Dict[str, Any]:
        """Get detailed container information"""
        if container_name not in self.containers:
            return {
                'status': 'error',
                'error': 'Container not found'
            }
        
        info = self.containers[container_name].copy()
        
        # Get Docker stats
        try:
            full_name = f"systerd-python-{container_name}"
            result = subprocess.run(
                ['docker', 'inspect', full_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                docker_info = json.loads(result.stdout)[0]
                info['docker_info'] = {
                    'status': docker_info['State']['Status'],
                    'running': docker_info['State']['Running'],
                    'pid': docker_info['State']['Pid'],
                    'started_at': docker_info['State']['StartedAt'],
                }
        except:
            pass
        
        return {
            'status': 'ok',
            'container': info
        }
