#!/usr/bin/env python3
"""Profiling utility for v0-strategy-engine-pro.

Usage:
    python scripts/profile.py --module trading --function main_loop
    python scripts/profile.py --module analytics --function compute_metrics
    python scripts/profile.py --help
"""

import argparse
import cProfile
import importlib
import io
import logging
import os
import pstats
import sys
from pathlib import Path
from datetime import datetime
from typing import Any, Callable

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create profile logs directory
PROFILE_LOGS_DIR = PROJECT_ROOT / 'profile_logs'
PROFILE_LOGS_DIR.mkdir(exist_ok=True)


def get_function(module_name: str, function_name: str) -> Callable:
    """Dynamically import and retrieve a function.
    
    Args:
        module_name: Name of the module (e.g., 'trading', 'analytics')
        function_name: Name of the function to profile
        
    Returns:
        The function object
        
    Raises:
        ImportError: If module or function not found
    """
    try:
        module = importlib.import_module(module_name)
        if not hasattr(module, function_name):
            raise AttributeError(f"Function '{function_name}' not found in module '{module_name}'")
        return getattr(module, function_name)
    except ImportError as e:
        logger.error(f"Failed to import module '{module_name}': {e}")
        raise


def profile_function(func: Callable, *args, **kwargs) -> pstats.Stats:
    """Profile a function using cProfile.
    
    Args:
        func: The function to profile
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        pstats.Stats object with profiling results
    """
    profiler = cProfile.Profile()
    profiler.enable()
    
    try:
        result = func(*args, **kwargs)
        logger.info(f"Function executed successfully: {func.__name__}")
    except Exception as e:
        logger.error(f"Error executing function: {e}")
        raise
    finally:
        profiler.disable()
    
    return pstats.Stats(profiler)


def print_stats(stats: pstats.Stats, num_stats: int = 20) -> None:
    """Print profiling statistics to console.
    
    Args:
        stats: pstats.Stats object
        num_stats: Number of top functions to display
    """
    print("\n" + "="*80)
    print(f"Top {num_stats} Functions by Cumulative Time:")
    print("="*80)
    stats.sort_stats('cumulative')
    stats.print_stats(num_stats)
    
    print("\n" + "="*80)
    print(f"Top {num_stats} Functions by Total Time:")
    print("="*80)
    stats.sort_stats('time')
    stats.print_stats(num_stats)


def save_stats(stats: pstats.Stats, module_name: str, function_name: str) -> str:
    """Save profiling statistics to file.
    
    Args:
        stats: pstats.Stats object
        module_name: Name of the profiled module
        function_name: Name of the profiled function
        
    Returns:
        Path to the saved file
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"profile_{module_name}_{function_name}_{timestamp}.txt"
    filepath = PROFILE_LOGS_DIR / filename
    
    with open(filepath, 'w') as f:
        # Redirect stdout to capture print output
        old_stdout = sys.stdout
        sys.stdout = f
        
        stats.sort_stats('cumulative')
        stats.print_stats(30)
        
        sys.stdout = old_stdout
    
    logger.info(f"Profile saved to: {filepath}")
    return str(filepath)


def main():
    """Main profiling entry point."""
    parser = argparse.ArgumentParser(
        description='Profile functions in v0-strategy-engine-pro',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/profile.py --module trading --function main_loop
  python scripts/profile.py --module analytics --function compute_metrics
  python scripts/profile.py --module ai_models --function predict
        """
    )
    
    parser.add_argument(
        '--module',
        required=True,
        help='Module name to profile (e.g., trading, analytics, ai_models)'
    )
    parser.add_argument(
        '--function',
        required=True,
        help='Function name to profile'
    )
    parser.add_argument(
        '--args',
        nargs='*',
        default=[],
        help='Positional arguments for the function'
    )
    parser.add_argument(
        '--kwargs',
        type=str,
        default='{}',
        help='Keyword arguments as JSON string'
    )
    parser.add_argument(
        '--save',
        action='store_true',
        help='Save profiling results to file'
    )
    parser.add_argument(
        '--stats-count',
        type=int,
        default=20,
        help='Number of top functions to display (default: 20)'
    )
    
    args = parser.parse_args()
    
    try:
        # Get the function to profile
        func = get_function(args.module, args.function)
        logger.info(f"Profiling {args.module}.{args.function}...")
        
        # Parse kwargs if provided
        import json
        try:
            kwargs = json.loads(args.kwargs)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON for kwargs: {args.kwargs}. Using empty dict.")
            kwargs = {}
        
        # Profile the function
        stats = profile_function(func, *args.args, **kwargs)
        
        # Print stats to console
        print_stats(stats, args.stats_count)
        
        # Save to file if requested
        if args.save:
            filepath = save_stats(stats, args.module, args.function)
            logger.info(f"Results saved to: {filepath}")
        
    except Exception as e:
        logger.error(f"Profiling failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
