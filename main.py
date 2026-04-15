"""
ScrapMaster Desktop - Main Entry Point
A production-ready desktop web scraping application
"""

import os
import sys
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def main():
    """Main entry point"""
    try:
        # Initialize application
        from app import logger
        
        # Check for service mode
        service_mode = '--service' in sys.argv
        
        logger.info(f"Starting ScrapMaster Desktop{' (service mode)' if service_mode else ''}")
        
        # Check Python version
        if sys.version_info < (3, 10):
            print("Error: Python 3.10+ required")
            sys.exit(1)
        
        # Launch GUI
        from app.gui.main_window import main as run_app
        from app.scheduler import job_scheduler
        
        # Start job scheduler
        job_scheduler.start()
        
        if service_mode:
            # Run in service mode (no GUI, just scheduler)
            logger.info("Running in service mode")
            import time
            while True:
                time.sleep(60)  # Keep alive
        else:
            run_app()
        
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()