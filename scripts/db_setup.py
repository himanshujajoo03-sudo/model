#!/usr/bin/env python3
"""
SIH26069 — Database Setup & Initialization Script
Comprehensive one-shot database and Kafka setup with verification.

Usage:
  python db_setup.py --help
  python db_setup.py                    # Full setup (db + kafka)
  python db_setup.py --db-only         # Database only
  python db_setup.py --kafka-only      # Kafka only
  python db_setup.py --verify          # Verify without running
  python db_setup.py --reset           # Clean slate (⚠️ DESTRUCTIVE)
"""

import sys
import subprocess
import time
import argparse
import logging
from typing import Optional, Tuple
from pathlib import Path

# Configuration
LOG_LEVEL = logging.INFO
TIMEOUT_SECONDS = 60
RETRY_ATTEMPTS = 3

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class DatabaseSetup:
    """Manages PostgreSQL database initialization."""
    
    def __init__(self, postgres_container: str = "weather-postgres"):
        self.container = postgres_container
        self.user = "weather"
        self.database = "weatherdb"
    
    def run_command(self, cmd: list, description: str = "") -> Tuple[bool, str]:
        """Execute a shell command in the PostgreSQL container."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
                check=False
            )
            if result.returncode == 0:
                logger.info(f"✓ {description}")
                return True, result.stdout
            else:
                logger.error(f"✗ {description}")
                logger.debug(f"Error output: {result.stderr}")
                return False, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"✗ {description} (timeout after {TIMEOUT_SECONDS}s)")
            return False, "Timeout"
        except Exception as e:
            logger.error(f"✗ {description} ({str(e)})")
            return False, str(e)
    
    def check_postgres_healthy(self) -> bool:
        """Verify PostgreSQL container is running and healthy."""
        cmd = [
            "docker", "exec", self.container,
            "pg_isready", "-U", self.user, "-d", self.database
        ]
        success, _ = self.run_command(cmd, f"Checking PostgreSQL health ({self.container})")
        return success
    
    def wait_for_postgres(self, retries: int = 10, delay: int = 2) -> bool:
        """Wait for PostgreSQL to become healthy."""
        for attempt in range(retries):
            if self.check_postgres_healthy():
                logger.info("✓ PostgreSQL is healthy")
                return True
            logger.info(f"  PostgreSQL not ready yet ({attempt+1}/{retries}), waiting {delay}s...")
            time.sleep(delay)
        logger.error("✗ PostgreSQL did not become healthy in time")
        return False
    
    def execute_sql_file(self, sql_file: Path, description: str = "") -> bool:
        """Execute a SQL file against the database."""
        if not sql_file.exists():
            logger.error(f"✗ SQL file not found: {sql_file}")
            return False
        
        desc = description or f"Executing {sql_file.name}"
        cmd = [
            "docker", "exec", "-T", self.container,
            "psql", "-U", self.user, "-d", self.database, "-v", "ON_ERROR_STOP=1",
            "-f", f"/migrations/{sql_file.name}"
        ]
        
        # Copy file into container first
        copy_cmd = ["docker", "cp", str(sql_file), f"{self.container}:/migrations/"]
        copy_success, _ = self.run_command(
            copy_cmd,
            f"Copying SQL file to container: {sql_file.name}"
        )
        if not copy_success:
            return False
        
        success, output = self.run_command(cmd, desc)
        if success and "NOTICE" in output:
            logger.info(f"  {output.strip()}")
        return success
    
    def initialize_schema(self) -> bool:
        """Initialize complete database schema."""
        logger.info("="*70)
        logger.info("PHASE 1: Database Schema Initialization")
        logger.info("="*70)
        
        if not self.wait_for_postgres():
            return False
        
        sql_file = Path("sql") / "00_complete_schema.sql"
        return self.execute_sql_file(sql_file, "Initializing complete schema")
    
    def verify_schema(self) -> bool:
        """Verify all required tables exist."""
        logger.info("="*70)
        logger.info("VERIFICATION: Database Schema")
        logger.info("="*70)
        
        required_tables = [
            'events',
            'canonical_events',
            'sources',
            'verification_log',
            'event_clusters',
            'verification_outbox',
            'event_cluster_members'
        ]
        
        cmd = [
            "docker", "exec", "-T", self.container,
            "psql", "-U", self.user, "-d", self.database, "-t",
            "-c", "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"
        ]
        
        success, output = self.run_command(cmd, "Listing tables")
        if not success:
            return False
        
        existing_tables = [line.strip() for line in output.strip().split('\n') if line.strip()]
        missing = [t for t in required_tables if t not in existing_tables]
        
        if missing:
            logger.error(f"✗ Missing tables: {', '.join(missing)}")
            logger.info(f"  Existing: {', '.join(existing_tables)}")
            return False
        
        logger.info(f"✓ All required tables exist:")
        for table in required_tables:
            count_cmd = [
                "docker", "exec", "-T", self.container,
                "psql", "-U", self.user, "-d", self.database, "-t",
                "-c", f"SELECT COUNT(*) FROM {table};"
            ]
            _, count = self.run_command(count_cmd, "")
            count_val = count.strip() if count else "0"
            logger.info(f"  • {table}: {count_val} rows")
        
        return True


class KafkaSetup:
    """Manages Kafka topic initialization."""
    
    def __init__(self, kafka_container: str = "weather-kafka"):
        self.container = kafka_container
        self.bootstrap_server = "localhost:9092"
        self.topics = [
            "weather.raw",
            "citizen.raw",
            "social.raw",
            "government.raw",
            "weather.processed",
            "weather.events",
            "weather.verified"
        ]
    
    def run_command(self, cmd: list, description: str = "") -> Tuple[bool, str]:
        """Execute a shell command."""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
                check=False
            )
            if result.returncode == 0:
                logger.info(f"✓ {description}")
                return True, result.stdout
            else:
                logger.error(f"✗ {description}")
                logger.debug(f"Error output: {result.stderr}")
                return False, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"✗ {description} (timeout after {TIMEOUT_SECONDS}s)")
            return False, "Timeout"
        except Exception as e:
            logger.error(f"✗ {description} ({str(e)})")
            return False, str(e)
    
    def check_kafka_healthy(self) -> bool:
        """Verify Kafka broker is accessible."""
        cmd = [
            "docker", "exec", self.container,
            "kafka-broker-api-versions", "--bootstrap-server", "localhost:9092"
        ]
        success, _ = self.run_command(cmd, f"Checking Kafka health ({self.container})")
        return success
    
    def wait_for_kafka(self, retries: int = 15, delay: int = 2) -> bool:
        """Wait for Kafka to become healthy."""
        for attempt in range(retries):
            if self.check_kafka_healthy():
                logger.info("✓ Kafka is healthy")
                return True
            logger.info(f"  Kafka not ready yet ({attempt+1}/{retries}), waiting {delay}s...")
            time.sleep(delay)
        logger.error("✗ Kafka did not become healthy in time")
        return False
    
    def create_topics(self) -> bool:
        """Create all required Kafka topics."""
        logger.info("="*70)
        logger.info("PHASE 2: Kafka Topic Initialization")
        logger.info("="*70)
        
        if not self.wait_for_kafka():
            return False
        
        all_success = True
        for topic in self.topics:
            cmd = [
                "docker", "exec", self.container,
                "kafka-topics",
                "--bootstrap-server", "localhost:9092",
                "--create",
                "--if-not-exists",
                "--topic", topic,
                "--partitions", "1",
                "--replication-factor", "1"
            ]
            success, _ = self.run_command(cmd, f"Creating topic: {topic}")
            all_success = all_success and success
        
        return all_success
    
    def verify_topics(self) -> bool:
        """Verify all required topics exist."""
        logger.info("="*70)
        logger.info("VERIFICATION: Kafka Topics")
        logger.info("="*70)
        
        cmd = [
            "docker", "exec", self.container,
            "kafka-topics",
            "--bootstrap-server", "localhost:9092",
            "--list"
        ]
        
        success, output = self.run_command(cmd, "Listing topics")
        if not success:
            return False
        
        existing_topics = [line.strip() for line in output.strip().split('\n') if line.strip()]
        missing = [t for t in self.topics if t not in existing_topics]
        
        if missing:
            logger.error(f"✗ Missing topics: {', '.join(missing)}")
            logger.info(f"  Existing: {', '.join(existing_topics)}")
            return False
        
        logger.info(f"✓ All required topics exist:")
        for topic in self.topics:
            logger.info(f"  • {topic}")
        
        return True


class SystemSetup:
    """Orchestrates complete system setup."""
    
    def __init__(self):
        self.db = DatabaseSetup()
        self.kafka = KafkaSetup()
    
    def run_full_setup(self) -> bool:
        """Execute complete database + Kafka setup."""
        logger.info("\n" + "="*70)
        logger.info("SIH26069 — Complete System Initialization")
        logger.info("="*70 + "\n")
        
        # Database
        if not self.db.initialize_schema():
            logger.error("\n✗ Database initialization failed")
            return False
        
        # Kafka
        if not self.kafka.create_topics():
            logger.error("\n✗ Kafka initialization failed")
            return False
        
        return True
    
    def verify_all(self) -> bool:
        """Verify database and Kafka setup."""
        logger.info("\n" + "="*70)
        logger.info("System Verification")
        logger.info("="*70 + "\n")
        
        db_ok = self.db.verify_schema()
        kafka_ok = self.kafka.verify_topics()
        
        return db_ok and kafka_ok
    
    def reset_all(self) -> bool:
        """Reset database and Kafka (DESTRUCTIVE)."""
        logger.warning("\n" + "="*70)
        logger.warning("⚠️  DESTRUCTIVE OPERATION: System Reset")
        logger.warning("="*70)
        logger.warning("This will DELETE all data:")
        logger.warning("  • PostgreSQL database contents")
        logger.warning("  • Kafka topics and messages")
        logger.warning("  • All streaming checkpoints")
        logger.warning("="*70 + "\n")
        
        response = input("Type 'RESET' to confirm: ").strip().upper()
        if response != "RESET":
            logger.info("Reset cancelled.")
            return False
        
        logger.info("Executing reset...")
        # Implementation would go here
        logger.error("Reset not yet implemented. Use: docker compose down -v")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="SIH26069 Database & Kafka Setup"
    )
    parser.add_argument(
        "--db-only",
        action="store_true",
        help="Initialize database only"
    )
    parser.add_argument(
        "--kafka-only",
        action="store_true",
        help="Initialize Kafka only"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify setup without changes"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset system (DESTRUCTIVE)"
    )
    
    args = parser.parse_args()
    system = SystemSetup()
    
    try:
        if args.reset:
            success = system.reset_all()
        elif args.verify:
            success = system.verify_all()
        elif args.db_only:
            success = system.db.initialize_schema()
        elif args.kafka_only:
            success = system.kafka.create_topics()
        else:
            success = system.run_full_setup()
        
        logger.info("\n" + "="*70)
        if success:
            logger.info("✓ Setup completed successfully")
        else:
            logger.error("✗ Setup encountered errors")
            sys.exit(1)
        logger.info("="*70 + "\n")
    
    except KeyboardInterrupt:
        logger.warning("\n✗ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"✗ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
