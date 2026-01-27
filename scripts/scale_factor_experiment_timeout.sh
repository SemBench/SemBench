#!/bin/bash

# scale_factor_experiment.sh - Run scale factor experiments across different scenarios
# Usage: ./script/scale_factor_experiment.sh

set -e

# ========================================
# CONFIGURATION SECTION
# Customize these variables as needed
# ========================================

# Scenarios to run (uncomment/comment to enable/disable)
# SCENARIOS=("movie" "ecomm" "animals" "mmqa" "cars")  # Run all scenarios
# SCENARIOS=("movie")  # Run only movie
# SCENARIOS=("ecomm")  # Run only ecomm
# SCENARIOS=("animals")  # Run only animals
# SCENARIOS=("mmqa")  # Run only mmqa
SCENARIOS=("cars")  # Run only cars

# Systems to run experiments on
SYSTEMS=("palimpzest" "thalamusdb" "bigquery" "lotus")

# Movie scenario configuration (base=2000)
MOVIE_SCALE_FACTORS=(1000 2000 4000 8000 16000)  # 0.5x, 1x, 2x, 4x, 8x base
MOVIE_QUERIES=(1 2 3 4 5 6 7 8 9 10)  # All queries

# Ecomm scenario configuration (base=500)
ECOMM_SCALE_FACTORS=(250 500 1000 2000 4000)  # 0.5x, 1x, 2x, 4x, 8x base
# ECOMM_SCALE_FACTORS=(2000 4000)  # 0.5x, 1x, 2x, 4x, 8x base
ECOMM_QUERIES=(1 2 3 4 5 6 7 8 9 10 11 12 13 14)  # All queries

# Animals scenario configuration (base=200)
ANIMALS_SCALE_FACTORS=(100 200 400 800 1600)  # 0.5x, 1x, 2x, 4x, 8x base
ANIMALS_QUERIES=(1 2 3 4 5 6 7 8 9 10)  # All queries

# MMQA scenario configuration (base=200)
MMQA_SCALE_FACTORS=(100 200 400 800)  # 0.5x, 1x, 2x, 4x base
MMQA_QUERIES=(1 2a 2b 3a 3f 4 5 6a 6b 6c 7)  # All queries

# Cars scenario configuration (base=19672)
CARS_SCALE_FACTORS=(9836 19672 39344 78688 157376)  # 0.5x, 1x, 2x, 4x, 8x base
CARS_QUERIES=(1 2 3 4 5 6 7 8 9 10)  # All queries

# General configuration
BASE_DIR="files"
MODEL_TAG="2.5flash"   # used in the target folder name
TIMEOUT_SECONDS=3600   # 1 hour timeout per query
NUM_REPEATS=5          # Number of times to repeat the entire experiment (set to >1 for repeated runs)

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
echo "Timeout per query: ${TIMEOUT_SECONDS}s"
echo ""

# Run all queries for a system at a given scale factor
run_all_queries_for_system() {
    local use_case=$1
    local system=$2
    local scale_factor=$3
    shift 3
    local queries=("$@")

    echo -e "${GREEN}Running ${system} | ${use_case} | SF=${scale_factor} | Queries: ${queries[*]}${NC}"

    local start_time=$(date +%s)

    # Run ALL queries together in one call
    python3 src/run.py \
        --systems "${system}" \
        --use-cases "${use_case}" \
        --queries "${queries[@]}" \
        --scale-factor "${scale_factor}" \
        --model "gemini-2.5-flash"

    local exit_code=$?
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    echo "  Total Duration: ${duration}s"

    if [[ ${exit_code} -ne 0 ]]; then
        echo -e "${RED}✗ System ${system} failed with exit code ${exit_code}${NC}"
        return 2
    fi

    echo -e "${GREEN}✓ All queries completed for ${system}${NC}"
    return 0
}

# Check if any query in the metrics file exceeded the timeout
check_for_timeouts() {
    local use_case=$1
    local system=$2
    local timeout_threshold=$3

    local metrics_file="${BASE_DIR}/${use_case}/metrics/${system}.json"

    echo "[DEBUG] Metrics file: ${metrics_file}"
    echo "[DEBUG] Timeout threshold: ${timeout_threshold}"

    if [[ ! -f "${metrics_file}" ]]; then
        echo -e "${YELLOW}⚠ Metrics file not found: ${metrics_file}${NC}"
        return 1
    fi

    # Use Python to parse JSON and check execution times
    # Output result as string to avoid bash exit code capture issues with set -e
    local result=$(python3 <<EOF
import json
import sys

try:
    with open('${metrics_file}', 'r') as f:
        data = json.load(f)

    timeout_threshold = ${timeout_threshold}

    print(f'[DEBUG-PY] Loaded {len(data)} queries', file=sys.stderr)
    print(f'[DEBUG-PY] Timeout threshold: {timeout_threshold}', file=sys.stderr)

    for query_id, query_data in data.items():
        if 'execution_time' in query_data:
            exec_time = query_data['execution_time']
            print(f'[DEBUG-PY] Query {query_id}: {exec_time}s', file=sys.stderr)
            if exec_time >= timeout_threshold:
                print(f'TIMEOUT|Query {query_id} took {exec_time:.2f}s (>= {timeout_threshold}s)')
                sys.exit(0)

    print('NO_TIMEOUT', file=sys.stderr)
    print('NO_TIMEOUT')
    sys.exit(0)
except Exception as e:
    print(f'ERROR|{e}')
    sys.exit(0)
EOF
)

    # Strip whitespace/newlines from result
    result=$(echo "${result}" | tr -d '\n\r')

    echo "[DEBUG] Python result: '${result}'"

    if [[ "${result}" == TIMEOUT* ]]; then
        local message="${result#TIMEOUT|}"
        echo -e "${RED}${message}${NC}"
        return 0  # Timeout detected
    elif [[ "${result}" == "NO_TIMEOUT" ]]; then
        echo "[DEBUG] Returning 1 (no timeout)"
        return 1  # No timeout
    else
        echo -e "${YELLOW}Unexpected result: ${result}${NC}"
        return 2  # Error
    fi
}

# Collect metrics for a scale factor
collect_metrics_for_scale_factor() {
    local use_case=$1
    local scale_factor=$2
    local repeat_num=$3
    shift 3
    local systems_to_collect=("$@")  # Only collect metrics for systems that ran

    echo -e "${YELLOW}Collecting metrics for ${use_case} | SF=${scale_factor} | Repeat ${repeat_num}...${NC}"

    local metrics_dir="${BASE_DIR}/${use_case}/metrics"
    local target_dir="${metrics_dir}/across_system_${MODEL_TAG}_sf${scale_factor}_repeat${repeat_num}"

    mkdir -p "${target_dir}"

    # Only collect metrics for systems that actually ran (not skipped due to timeout)
    for system in "${systems_to_collect[@]}"; do
        local source_file="${metrics_dir}/${system}.json"
        if [[ -f "${source_file}" ]]; then
            cp "${source_file}" "${target_dir}/"
            echo "  ✓ Collected ${use_case}/${system}.json → ${target_dir}/"
        else
            echo -e "  ${YELLOW}⚠ Warning: ${use_case}/${system}.json not found${NC}"
        fi
    done
    echo ""
}

# Run experiments for a single scenario with all its scale factors
run_scenario_experiments() {
    local use_case=$1
    local repeat_num=$2
    shift 2
    local scale_factors=("$@")

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Starting experiments for scenario: ${use_case} | Repeat ${repeat_num}${NC}"
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
        "animals")
            queries=("${ANIMALS_QUERIES[@]}")
            ;;
        "mmqa")
            queries=("${MMQA_QUERIES[@]}")
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

    # Track which systems have timed out (associative array simulation)
    declare -A system_timed_out
    for system in "${SYSTEMS[@]}"; do
        system_timed_out["${system}"]=false
    done

    # Iterate through scale factors from small to large
    for scale_factor in "${scale_factors[@]}"; do
        echo -e "${BLUE}--- Scale Factor: ${scale_factor} ---${NC}"

        # Track which systems actually ran for this scale factor
        local systems_ran=()

        # Run all systems for this scale factor
        for system in "${SYSTEMS[@]}"; do
            # Skip this system if it already timed out at a previous scale factor
            if [[ "${system_timed_out[${system}]}" == true ]]; then
                echo -e "${YELLOW}⚠ Skipping ${system} (timed out at previous scale factor)${NC}"
                continue
            fi

            echo -e "${YELLOW}Running system: ${system}${NC}"

            # Run ALL queries for this system in one call
            run_all_queries_for_system "${use_case}" "${system}" "${scale_factor}" "${queries[@]}"
            local exec_result=$?

            if [[ ${exec_result} -eq 2 ]]; then
                echo -e "${YELLOW}System ${system} failed but continuing with other systems...${NC}"
                continue
            fi

            # After successful execution, check if any query exceeded timeout
            echo "[DEBUG] Calling check_for_timeouts with threshold=${TIMEOUT_SECONDS}"

            # Temporarily disable exit-on-error to capture return code
            set +e
            check_for_timeouts "${use_case}" "${system}" "${TIMEOUT_SECONDS}"
            local timeout_result=$?
            set -e

            echo "[DEBUG] check_for_timeouts returned: ${timeout_result}"

            if [[ ${timeout_result} -eq 0 ]]; then
                echo -e "${YELLOW}⚠ Timeout detected for ${system} at ${use_case} SF=${scale_factor}${NC}"
                echo -e "${YELLOW}   ${system} will skip larger scale factors but other systems will continue${NC}"
                system_timed_out["${system}"]=true
            else
                echo "[DEBUG] No timeout detected (result=${timeout_result})"
            fi

            # Add this system to the list of systems that ran (regardless of timeout status)
            # We still want to collect metrics for systems that timed out at THIS scale factor
            systems_ran+=("${system}")

            echo ""
        done

        # Collect metrics ONLY for systems that ran at this scale factor
        # This prevents copying old metrics from timed-out systems at previous scale factors
        collect_metrics_for_scale_factor "${use_case}" "${scale_factor}" "${repeat_num}" "${systems_ran[@]}"

        echo -e "${GREEN}✓ Completed all systems for ${use_case} SF=${scale_factor} | Repeat ${repeat_num}${NC}"
        echo ""
    done

    echo -e "${GREEN}✓ Finished scenario: ${use_case} | Repeat ${repeat_num}${NC}"
    echo ""
}

# ========================================
# MAIN EXECUTION
# ========================================

main() {
    echo -e "${BLUE}Starting scale factor experiments...${NC}"
    echo -e "${BLUE}Scenarios to run: ${SCENARIOS[*]}${NC}"
    echo -e "${BLUE}Number of repeats: ${NUM_REPEATS}${NC}"
    echo ""

    # Outer loop for repeats
    for ((repeat=1; repeat<=NUM_REPEATS; repeat++)); do
        echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║          STARTING REPEAT ${repeat} of ${NUM_REPEATS}                    ║${NC}"
        echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
        echo ""

        # Run scenarios based on configuration
        for scenario in "${SCENARIOS[@]}"; do
            case "${scenario}" in
                "movie")
                    run_scenario_experiments "movie" "${repeat}" "${MOVIE_SCALE_FACTORS[@]}"
                    ;;
                "ecomm")
                    run_scenario_experiments "ecomm" "${repeat}" "${ECOMM_SCALE_FACTORS[@]}"
                    ;;
                "animals")
                    run_scenario_experiments "animals" "${repeat}" "${ANIMALS_SCALE_FACTORS[@]}"
                    ;;
                "mmqa")
                    run_scenario_experiments "mmqa" "${repeat}" "${MMQA_SCALE_FACTORS[@]}"
                    ;;
                "cars")
                    run_scenario_experiments "cars" "${repeat}" "${CARS_SCALE_FACTORS[@]}"
                    ;;
                *)
                    echo -e "${RED}Unknown scenario: ${scenario}. Skipping...${NC}"
                    ;;
            esac
        done

        echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
        echo -e "${GREEN}║          COMPLETED REPEAT ${repeat} of ${NUM_REPEATS}                  ║${NC}"
        echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
        echo ""
    done

    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}=== All Scale Factor Experiments Complete! ===${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Results stored in:"
    for scenario in "${SCENARIOS[@]}"; do
        echo "  ${BASE_DIR}/${scenario}/metrics/across_system_${MODEL_TAG}_sf*_repeat*/"
    done
    echo ""
}

# Run main function
main
