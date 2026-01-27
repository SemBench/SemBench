#!/bin/bash

# scale_factor_experiment.sh - Run scale factor experiments across different scenarios
# Usage: ./script/scale_factor_experiment.sh

set -e

# ========================================
# CONFIGURATION SECTION
# Customize these variables as needed
# ========================================

# Scenarios to run (uncomment/comment to enable/disable)
SCENARIOS=("movie" "ecomm" "mmqa" "animals" "cars")  # Run all scenarios

# Systems to run experiments on
SYSTEMS=("palimpzest" "thalamusdb" "bigquery" "lotus") 

# Movie scenario configuration
MOVIE_SCALE_FACTORS=(1000 2000 4000 8000 16000)
MOVIE_QUERIES=(1 2 3 4 5 6 7 8 9 10)

# Ecomm scenario configuration
ECOMM_SCALE_FACTORS=(250 500 1000 2000 4000)
ECOMM_QUERIES=(1 2 3 4 5 6 7 8 9 10 11 12 13 14)

# MMQA scenario configuration
MMQA_SCALE_FACTORS=(100 200 400 800)
MMQA_QUERIES=(1 2a 2b 3a 3f 4 5 6a 6b 6c 7)  # Full query set

# Animals scenario configuration
ANIMALS_SCALE_FACTORS=(100 200 400 800 1600)  # Define your scale factors
ANIMALS_QUERIES=(1 2 3 4 5 6 7 8 9 10)  # Define your query IDs

# Cars scenario configuration
CARS_SCALE_FACTORS=(9836 19672 39344 78688 157376)
CARS_QUERIES=(1 2 3 4 5 6 7 8 9 10)

# General configuration
BASE_DIR="files"
MODEL_TAG="2.5flash"   # used in the target folder name
ENABLE_MEMORY_TRACKING=true  # Enable memory measurement using /usr/bin/time

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ========================================
# HELPER FUNCTIONS
# ========================================

echo -e "${BLUE}=== SemBench Scale Factor Experiment Runner ===${NC}"
echo "Running scale factor experiments..."
echo "Systems: ${SYSTEMS[*]}"
echo "Memory tracking: ${ENABLE_MEMORY_TRACKING}"
echo ""

# Parse peak memory from /usr/bin/time output
parse_peak_memory() {
    local time_output_file=$1

    if [[ ! -f "${time_output_file}" ]]; then
        echo "0"
        return
    fi

    # Extract "Maximum resident set size" in KB and convert to MB
    local memory_kb=$(grep "Maximum resident set size" "${time_output_file}" | awk '{print $6}')

    if [[ -z "${memory_kb}" ]]; then
        echo "0"
    else
        # Convert KB to MB
        echo "scale=2; ${memory_kb} / 1024" | bc
    fi
}

# Store memory metric for a query
store_memory_metric() {
    local use_case=$1
    local system=$2
    local query_id=$3
    local memory_mb=$4

    local memory_file="${BASE_DIR}/${use_case}/metrics/${system}_memory.json"

    # Create or update the memory metrics JSON file
    if [[ ! -f "${memory_file}" ]]; then
        echo "{}" > "${memory_file}"
    fi

    # Use Python to update the JSON file
    python3 <<EOF
import json

memory_file = "${memory_file}"
query_id = "${query_id}"
memory_mb = ${memory_mb}

try:
    with open(memory_file, 'r') as f:
        data = json.load(f)
except:
    data = {}

if query_id not in data:
    data[query_id] = {}

data[query_id]["peak_memory_mb"] = memory_mb

with open(memory_file, 'w') as f:
    json.dump(data, f, indent=2)

print(f"Stored memory metric: Q{query_id} = {memory_mb:.2f} MB")
EOF
}

# Merge individual query metrics into a single JSON file
merge_query_metrics() {
    local temp_dir=$1
    local output_file=$2

    # Use Python to merge all JSON files
    python3 <<EOF
import json
import os
import glob

temp_dir = "${temp_dir}"
output_file = "${output_file}"

merged_metrics = {}

# Find all query JSON files in temp directory
query_files = glob.glob(os.path.join(temp_dir, "Q*.json"))

if not query_files:
    print("Warning: No query metrics files found to merge")
else:
    # Read and merge each query's metrics
    for query_file in sorted(query_files):
        try:
            with open(query_file, 'r') as f:
                query_metrics = json.load(f)
                # Merge the query metrics into the combined dictionary
                merged_metrics.update(query_metrics)
        except Exception as e:
            print(f"Error reading {query_file}: {e}")

    # Write merged metrics to output file
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(merged_metrics, f, indent=2)

    print(f"Merged {len(query_files)} query metrics into {output_file}")
EOF
}

# Run all queries for a system at a given scale factor
run_all_queries_for_system() {
    local use_case=$1
    local system=$2
    local scale_factor=$3
    shift 3
    local queries=("$@")

    echo -e "${GREEN}Running ${system} | ${use_case} | SF=${scale_factor} | Queries: ${queries[*]}${NC}"

    local start_time=$(date +%s)
    local total_failed=0

    local metrics_dir="${BASE_DIR}/${use_case}/metrics"
    local temp_metrics_dir="/tmp/sembench_metrics_${use_case}_${system}_${scale_factor}"

    # Create temporary directory for storing individual query metrics
    mkdir -p "${temp_metrics_dir}"

    # Clear the main metrics file before starting queries
    local main_metrics_file="${metrics_dir}/${system}.json"
    rm -f "${main_metrics_file}"

    # Run each query individually to measure per-query memory
    for query in "${queries[@]}"; do
        echo -e "${YELLOW}  Running Q${query}...${NC}"

        local query_start=$(date +%s)

        if [[ "${ENABLE_MEMORY_TRACKING}" == "true" ]]; then
            # Use /usr/bin/time to measure memory
            local time_output="/tmp/time_output_${system}_${use_case}_${scale_factor}_${query}.txt"

            /usr/bin/time -v -o "${time_output}" python3 src/run.py \
                --systems "${system}" \
                --use-cases "${use_case}" \
                --queries "${query}" \
                --scale-factor "${scale_factor}" \
                --model "gemini-2.5-flash" 2>&1

            local exit_code=$?

            # Parse and store memory metric
            local peak_memory=$(parse_peak_memory "${time_output}")
            echo "    Peak Memory: ${peak_memory} MB"
            store_memory_metric "${use_case}" "${system}" "${query}" "${peak_memory}"

            # Clean up time output file
            rm -f "${time_output}"
        else
            # Run without memory tracking
            python3 src/run.py \
                --systems "${system}" \
                --use-cases "${use_case}" \
                --queries "${query}" \
                --scale-factor "${scale_factor}" \
                --model "gemini-2.5-flash"

            local exit_code=$?
        fi

        local query_end=$(date +%s)
        local query_duration=$((query_end - query_start))

        if [[ ${exit_code} -ne 0 ]]; then
            echo -e "${RED}    ✗ Q${query} failed with exit code ${exit_code}${NC}"
            total_failed=$((total_failed + 1))
        else
            echo -e "${GREEN}    ✓ Q${query} completed (${query_duration}s)${NC}"

            # Save the metrics file for this query to temp directory
            if [[ -f "${main_metrics_file}" ]]; then
                cp "${main_metrics_file}" "${temp_metrics_dir}/Q${query}.json"
            fi
        fi
    done

    # Merge all individual query metrics into the final metrics file
    echo -e "${YELLOW}  Merging metrics from ${#queries[@]} queries...${NC}"
    merge_query_metrics "${temp_metrics_dir}" "${main_metrics_file}"

    # Clean up temporary directory
    rm -rf "${temp_metrics_dir}"

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    echo "  Total Duration: ${duration}s"

    if [[ ${total_failed} -gt 0 ]]; then
        echo -e "${RED}✗ ${total_failed}/${#queries[@]} queries failed for ${system}${NC}"
        return 2
    fi

    echo -e "${GREEN}✓ All queries completed for ${system}${NC}"
    return 0
}

# Collect metrics for a scale factor
collect_metrics_for_scale_factor() {
    local use_case=$1
    local scale_factor=$2

    echo -e "${YELLOW}Collecting metrics for ${use_case} | SF=${scale_factor}...${NC}"

    local metrics_dir="${BASE_DIR}/${use_case}/metrics"
    local target_dir="${metrics_dir}/across_system_${MODEL_TAG}_sf${scale_factor}"

    mkdir -p "${target_dir}"

    for system in "${SYSTEMS[@]}"; do
        # Copy regular metrics
        local source_file="${metrics_dir}/${system}.json"
        if [[ -f "${source_file}" ]]; then
            cp "${source_file}" "${target_dir}/"
            echo "  ✓ Collected ${use_case}/${system}.json → ${target_dir}/"
        else
            echo -e "  ${YELLOW}⚠ Warning: ${use_case}/${system}.json not found${NC}"
        fi

        # Copy memory metrics if they exist
        local memory_file="${metrics_dir}/${system}_memory.json"
        if [[ -f "${memory_file}" ]]; then
            cp "${memory_file}" "${target_dir}/"
            echo "  ✓ Collected ${use_case}/${system}_memory.json → ${target_dir}/"
        fi
    done
    echo ""
}

# Run experiments for a single scenario with all its scale factors
run_scenario_experiments() {
    local use_case=$1
    shift
    local scale_factors=("$@")

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Starting experiments for scenario: ${use_case}${NC}"
    echo -e "${BLUE}Scale factors: ${scale_factors[*]}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Get queries for this scenario
    local queries=()
    case "${use_case}" in
        "movie")
            queries=("${MOVIE_QUERIES[@]}")
            ;;
        "ecomm")
            queries=("${ECOMM_QUERIES[@]}")
            ;;
        "mmqa")
            queries=("${MMQA_QUERIES[@]}")
            ;;
        "animals")
            queries=("${ANIMALS_QUERIES[@]}")
            ;;
        "cars")
            queries=("${CARS_QUERIES[@]}")
            ;;
        *)
            echo -e "${RED}Unknown scenario: ${use_case}${NC}"
            return 1
            ;;
    esac

    echo "Queries to run: ${queries[*]}"
    echo ""

    # Iterate through scale factors from small to large
    for scale_factor in "${scale_factors[@]}"; do
        echo -e "${BLUE}--- Scale Factor: ${scale_factor} ---${NC}"

        # Run all systems for this scale factor
        for system in "${SYSTEMS[@]}"; do
            echo -e "${YELLOW}Running system: ${system}${NC}"

            # Run ALL queries for this system in one call
            run_all_queries_for_system "${use_case}" "${system}" "${scale_factor}" "${queries[@]}"
            local exec_result=$?

            if [[ ${exec_result} -eq 2 ]]; then
                echo -e "${YELLOW}System ${system} had failures but continuing with other systems...${NC}"
                continue
            fi

            echo ""
        done

        # Collect metrics for this scale factor (after ALL systems complete)
        collect_metrics_for_scale_factor "${use_case}" "${scale_factor}"

        echo -e "${GREEN}✓ Completed all systems for ${use_case} SF=${scale_factor}${NC}"
        echo ""
    done

    echo -e "${GREEN}✓ Finished scenario: ${use_case}${NC}"
    echo ""
}

# ========================================
# MAIN EXECUTION
# ========================================

main() {
    echo -e "${BLUE}Starting scale factor experiments...${NC}"
    echo -e "${BLUE}Scenarios to run: ${SCENARIOS[*]}${NC}"
    echo ""

    # Run scenarios based on configuration
    for scenario in "${SCENARIOS[@]}"; do
        case "${scenario}" in
            "movie")
                run_scenario_experiments "movie" "${MOVIE_SCALE_FACTORS[@]}"
                ;;
            "ecomm")
                run_scenario_experiments "ecomm" "${ECOMM_SCALE_FACTORS[@]}"
                ;;
            "mmqa")
                run_scenario_experiments "mmqa" "${MMQA_SCALE_FACTORS[@]}"
                ;;
            "animals")
                run_scenario_experiments "animals" "${ANIMALS_SCALE_FACTORS[@]}"
                ;;
            "cars")
                run_scenario_experiments "cars" "${CARS_SCALE_FACTORS[@]}"
                ;;
            *)
                echo -e "${RED}Unknown scenario: ${scenario}. Skipping...${NC}"
                ;;
        esac
    done

    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}=== All Scale Factor Experiments Complete! ===${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Results stored in:"
    for scenario in "${SCENARIOS[@]}"; do
        echo "  ${BASE_DIR}/${scenario}/metrics/across_system_${MODEL_TAG}_sf*/"
    done
    echo ""

    if [[ "${ENABLE_MEMORY_TRACKING}" == "true" ]]; then
        echo -e "${BLUE}Memory metrics stored in:${NC}"
        for scenario in "${SCENARIOS[@]}"; do
            echo "  ${BASE_DIR}/${scenario}/metrics/*_memory.json"
        done
        echo ""
    fi
}

# Run main function
main
