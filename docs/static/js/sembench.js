// SemBench Website JavaScript

$(document).ready(function() {
    console.log('SemBench website loaded');
    
    // Initialize the website
    init();
});

// Global variables
let currentVersion = null; // Selected version for interactive table
let currentPerformanceVersion = null; // Selected version for performance comparison
let currentScenario = null; // Selected scenario
let currentModel = null; // Selected model
let systemsData = {};
let coverageData = null; // Coverage data for current scenario
let colorblindMode = false; // Colorblind-friendly mode toggle
let availableVersions = []; // Available versions from versions.json
let systemVersions = {}; // System version numbers from system_version.json
let scenarioData = {
    'animals': {
        'models': ['2.0flash', '2.5flash', '5mini'],
        'modelNames': {
            '2.0flash': 'Gemini 2.0 Flash',
            '2.5flash': 'Gemini 2.5 Flash',
            '5mini': 'GPT-4o Mini (5mini)'
        },
        'pathPrefix': 'across_system_' // animals uses across_system_ without 's'
    },
    'movie': {
        'models': ['2.0flash', '2.5flash', '4omini', '5mini'],
        'modelNames': {
            '2.0flash': 'Gemini 2.0 Flash',
            '2.5flash': 'Gemini 2.5 Flash',
            '4omini': 'GPT-4o Mini',
            '5mini': 'GPT-4o Mini (5mini)'
        },
        'pathPrefix': 'across_system_' // movie uses across_system_ without 's'
    },
    'medical': {
        'models': ['2.5flash', '2.5pro', '5mini'],
        'modelNames': {
            '2.5flash': 'Gemini 2.5 Flash',
            '2.5pro': 'Gemini 2.5 Pro',
            '5mini': 'GPT-5 Mini'
        },
        'pathPrefix': 'across_system_' // movie uses across_system_ without 's'
    },
    'ecomm': {
        'models': ['2.5flash', '2.5flashlite', '2.5pro', '4o', '4omini'],
        'modelNames': {
            '2.5flash': 'Gemini 2.5 Flash',
            '2.5flashlite': 'Gemini 2.5 Flash Lite',
            '2.5pro': 'Gemini 2.5 Pro',
            '4o': 'GPT-4o',
            '4omini': 'GPT-4o Mini'
        },
        'pathPrefix': 'across_system_',
        'queries': ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'Q7', 'Q8', 'Q9', 'Q10', 'Q11', 'Q12', 'Q13', 'Q14'] // E-commerce has 14 queries
    },
    'mmqa': {
        'models': ['gemini-2.5-flash'],
        'modelNames': {
            'gemini-2.5-flash': 'Gemini 2.5 Flash'
        },
        'pathPrefix': 'across_system_', // mmqa uses across_system_ without 's'
        'queries': ['Q1', 'Q2a', 'Q2b', 'Q3a', 'Q3f', 'Q4', 'Q5', 'Q6a', 'Q6b', 'Q6c', 'Q7'] // Custom query list for MMQA
    }
};

function init() {
    // Set up event listeners
    $('#versionSelect').change(onVersionChange);
    $('#performanceVersionSelect').change(onPerformanceVersionChange);
    $('#scenarioSelect').change(onScenarioChange);
    $('#modelSelect').change(onModelChange);
    $('#colorblindToggle').change(onColorblindToggleChange);

    // Set up query link clicks
    $(document).on('click', '.query-link', onQueryClick);
    
    // Set up FAQ toggles
    $('.faq-question').click(function() {
        const answer = $(this).next('.faq-answer');
        const isVisible = answer.is(':visible');
        
        // Close all other FAQ answers first
        $('.faq-answer').slideUp(300);
        $('.faq-question').removeClass('active');
        
        // If this one wasn't visible, show it
        if (!isVisible) {
            answer.slideDown(300);
            $(this).addClass('active');
        }
    });
    
    // Load available versions and initialize
    loadAvailableVersions().then(() => {
        console.log('Initialization complete');
    });

    console.log('Setting up website...');
}

async function loadAvailableVersions() {
    try {
        console.log('Loading available versions...');
        const response = await fetch('static/versions.json');

        if (!response.ok) {
            console.warn('No versions.json found, falling back to legacy mode');
            // Fallback to legacy mode (direct files access)
            currentVersion = 'legacy';
            enableLegacyMode();
            return;
        }

        const versionsData = await response.json();
        availableVersions = versionsData.versions || [];

        // Populate both version selectors
        const versionSelect = $('#versionSelect');
        const performanceVersionSelect = $('#performanceVersionSelect');

        versionSelect.html('<option value="">Select Version</option>');
        performanceVersionSelect.html('<option value="">Select Version</option>');

        availableVersions.forEach(version => {
            versionSelect.append(`<option value="${version.name}">${version.name}</option>`);
            performanceVersionSelect.append(`<option value="${version.name}">${version.name}</option>`);
        });

        // Set default versions if available
        if (versionsData.default_version) {
            // Set default for interactive table
            currentVersion = versionsData.default_version;
            versionSelect.val(currentVersion);

            // Set default for performance comparison
            currentPerformanceVersion = versionsData.default_version;
            performanceVersionSelect.val(currentPerformanceVersion);

            // Update tolerance analysis image for the selected version
            updateToleranceAnalysisImage();

            // Set default scenario and model
            currentScenario = 'movie';
            currentModel = '2.5flash';

            // Enable and populate controls
            $('#scenarioSelect').prop('disabled', false).val(currentScenario);
            populateModelSelect();
            $('#modelSelect').prop('disabled', false).val(currentModel);

            // Load the data immediately
            loadBenchmarkData();
        }

        console.log(`Loaded ${availableVersions.length} versions`);
    } catch (error) {
        console.error('Error loading versions:', error);
        // Fallback to legacy mode
        currentVersion = 'legacy';
        enableLegacyMode();
    }
}

function enableLegacyMode() {
    console.log('Running in legacy mode - using direct files access');
    $('#versionSelect').prop('disabled', true).html('<option value="legacy">Legacy Mode</option>');
    $('#performanceVersionSelect').prop('disabled', true).html('<option value="legacy">Legacy Mode</option>');
    $('#scenarioSelect').prop('disabled', false);

    // Set legacy mode for both version types
    currentPerformanceVersion = 'legacy';
    updateToleranceAnalysisImage();

    // Set default values for legacy mode
    currentScenario = 'movie';
    currentModel = '2.5flash';
    $('#scenarioSelect').val(currentScenario);
    populateModelSelect();
    $('#modelSelect').prop('disabled', false).val(currentModel);
    loadBenchmarkData();
}

function onVersionChange() {
    currentVersion = $('#versionSelect').val();
    console.log('Interactive table version changed to:', currentVersion);

    if (currentVersion) {
        // Enable scenario selection
        $('#scenarioSelect').prop('disabled', false);

        // Reset dependent selections
        currentScenario = null;
        currentModel = null;
        $('#scenarioSelect').val('');
        $('#modelSelect').prop('disabled', true).html('<option value="">Select Model</option>');

        // Hide table and other sections
        $('#benchmarkTable').hide();
        $('#queryDetails').hide();
        $('#overallPerformance').hide();
    } else {
        // Reset everything
        $('#scenarioSelect').prop('disabled', true).val('');
        $('#modelSelect').prop('disabled', true).html('<option value="">Select Model</option>');
        $('#benchmarkTable').hide();
        $('#queryDetails').hide();
        $('#overallPerformance').hide();
    }
}

function onPerformanceVersionChange() {
    currentPerformanceVersion = $('#performanceVersionSelect').val();
    console.log('Performance comparison version changed to:', currentPerformanceVersion);

    // Update tolerance analysis image for the selected version
    updateToleranceAnalysisImage();
}

function onScenarioChange() {
    currentScenario = $('#scenarioSelect').val();
    console.log('Scenario changed to:', currentScenario);

    if (currentScenario) {
        // Enable model select and populate it
        populateModelSelect();
        $('#modelSelect').prop('disabled', false);

        // Auto-select default model based on scenario
        const availableModels = scenarioData[currentScenario].models;
        let defaultModel = null;

        // For MMQA, use gemini-2.5-flash; for others, use 2.5flash
        if (currentScenario === 'mmqa' && availableModels.includes('gemini-2.5-flash')) {
            defaultModel = 'gemini-2.5-flash';
        } else if (availableModels.includes('2.5flash')) {
            defaultModel = '2.5flash';
        }

        if (defaultModel) {
            currentModel = defaultModel;
            $('#modelSelect').val(currentModel);

            // Load data immediately
            if (currentVersion) {
                loadBenchmarkData();
            }
        } else {
            // No default model available, hide table until model is selected
            $('#benchmarkTable').hide();
            $('#queryDetails').hide();
            $('#overallPerformance').hide();
        }
    } else {
        // Reset everything
        $('#modelSelect').prop('disabled', true).html('<option value="">Select Model</option>');
        $('#benchmarkTable').hide();
        $('#queryDetails').hide();
        $('#overallPerformance').hide();
    }
}

function populateModelSelect() {
    const modelSelect = $('#modelSelect');
    modelSelect.html('<option value="">Select Model</option>');
    
    if (scenarioData[currentScenario]) {
        const models = scenarioData[currentScenario].models;
        const modelNames = scenarioData[currentScenario].modelNames;
        
        models.forEach(model => {
            const displayName = modelNames[model] || model;
            modelSelect.append(`<option value="${model}">${displayName}</option>`);
        });
    }
}

function onModelChange() {
    currentModel = $('#modelSelect').val();
    console.log('Model changed to:', currentModel);

    if (currentModel && currentScenario && currentVersion) {
        // Load data and show table
        loadBenchmarkData();
    } else {
        $('#benchmarkTable').hide();
        $('#queryDetails').hide();
        $('#overallPerformance').hide();
    }
}

function onColorblindToggleChange() {
    colorblindMode = $('#colorblindToggle').is(':checked');
    console.log('Colorblind mode changed to:', colorblindMode);

    // Update the table if it's already displayed
    if ($('#benchmarkTable').is(':visible')) {
        populateTable();
    }
}

function getDataBasePath() {
    if (currentVersion === 'legacy') {
        return '../files';
    } else {
        return `static/data/${currentVersion}`;
    }
}

function getFiguresBasePath() {
    if (currentVersion === 'legacy') {
        return '../figures';
    } else {
        return `static/figures/${currentVersion}`;
    }
}

function updateToleranceAnalysisImage() {
    const toleranceAnalysisImage = $('#toleranceAnalysisImage');
    const errorMessage = toleranceAnalysisImage.next('p');

    if (currentPerformanceVersion === 'legacy') {
        // Use the original static path for legacy mode
        toleranceAnalysisImage.attr('src', 'static/images/tolerance_analysis_plots_custom_ranges.png');
    } else if (currentPerformanceVersion) {
        // Use versioned path based on performance version selection
        toleranceAnalysisImage.attr('src', `static/figures/${currentPerformanceVersion}/tolerance_analysis_plots_custom_ranges.png`);
    } else {
        // No version selected, hide image
        toleranceAnalysisImage.hide();
        errorMessage.show();
        return;
    }

    // Reset error state
    toleranceAnalysisImage.show();
    errorMessage.hide();
}

async function loadBenchmarkData() {
    try {
        console.log(`Loading data for ${currentScenario} with ${currentModel} (version: ${currentVersion})`);

        // Show loading state
        showLoading();

        // Load coverage data for current scenario
        coverageData = await loadCoverageData();

        // Load system versions
        systemVersions = await loadSystemVersions();

        // Load data with round aggregation if available, fallback to single run
        systemsData = await loadDataWithRoundSupport();

        // Populate the table
        populateTable();

        // Show table and performance charts
        $('#benchmarkTable').show();
        showPerformanceCharts();

        // Hide loading state
        hideLoading();

    } catch (error) {
        console.error('Error loading benchmark data:', error);
        showError('Failed to load benchmark data');
    }
}

async function loadDataWithRoundSupport() {
    const pathPrefix = scenarioData[currentScenario].pathPrefix;
    
    // First, check if multiple rounds are available
    const roundData = await loadMultipleRounds();
    
    if (roundData.hasMultipleRounds) {
        console.log(`Found ${roundData.roundCount} rounds, calculating mean and std`);
        return calculateAggregatedMetrics(roundData.allRoundsData);
    } else {
        console.log('No multiple rounds found, loading single run data');
        return await loadSingleRunData();
    }
}

async function loadMultipleRounds() {
    const pathPrefix = scenarioData[currentScenario].pathPrefix;
    const possibleSystems = ['bigquery', 'lotus', 'palimpzest', 'thalamusdb', 'snowflake'];
    const allRoundsData = {};
    let roundCount = 0;
    
    // Check for rounds 1-5
    for (let round = 1; round <= 5; round++) {
        const roundFolder = `${pathPrefix}${currentModel}_${round}`;
        const roundData = {};
        let hasDataInRound = false;
        
        for (const system of possibleSystems) {
            try {
                const dataPath = `${getDataBasePath()}/${currentScenario}/metrics/${roundFolder}/${system}.json`;
                const response = await fetch(dataPath);
                if (response.ok) {
                    const responseText = await response.text();
                    const sanitizedResponseText = responseText
                        .replace(/\bNaN\b/g, 'null')
                        .replace(/\bInfinity\b/g, 'null')
                        .replace(/\b-Infinity\b/g, 'null');
                    roundData[system] = JSON.parse(sanitizedResponseText);
                    hasDataInRound = true;
                }
            } catch (error) {
                // File doesn't exist, continue
            }
        }
        
        if (hasDataInRound) {
            allRoundsData[round] = roundData;
            roundCount++;
        }
    }
    
    return {
        hasMultipleRounds: roundCount > 1,
        roundCount: roundCount,
        allRoundsData: allRoundsData
    };
}

async function loadSingleRunData() {
    const pathPrefix = scenarioData[currentScenario].pathPrefix;
    const possibleSystems = ['bigquery', 'lotus', 'palimpzest', 'thalamusdb', 'snowflake'];
    const systemsData = {};
    for (const system of possibleSystems) {
        try {
            const dataPath = `${getDataBasePath()}/${currentScenario}/metrics/${pathPrefix}${currentModel}/${system}.json`;
            const response = await fetch(dataPath);
            if (response.ok) {
                const responseText = await response.text();
                const sanitizedResponseText = responseText
                    .replace(/\bNaN\b/g, 'null')
                    .replace(/\bInfinity\b/g, 'null')
                    .replace(/\b-Infinity\b/g, 'null');
                systemsData[system] = JSON.parse(sanitizedResponseText);
            }
        } catch (error) {
            console.warn(`Could not load data for system: ${system}`, error);
        }
    
    }
    
    return systemsData;
}

function calculateAggregatedMetrics(allRoundsData) {
    const aggregatedData = {};
    const systems = new Set();
    const queries = new Set();
    
    // Collect all systems and queries
    Object.values(allRoundsData).forEach(roundData => {
        Object.keys(roundData).forEach(system => {
            systems.add(system);
            Object.keys(roundData[system]).forEach(query => {
                if (query.startsWith('Q')) {
                    queries.add(query);
                }
            });
        });
    });
    
    // Calculate mean and std for each system and query
    systems.forEach(system => {
        aggregatedData[system] = {};
        
        queries.forEach(query => {
            const values = {
                money_cost: [],
                execution_time: [],
                quality: []
            };
            
            // Collect values across all rounds
            Object.values(allRoundsData).forEach(roundData => {
                if (roundData[system] && roundData[system][query]) {
                    const queryData = roundData[system][query];

                    // Only include if has positive cost (matches Python logic)
                    if (queryData.money_cost > 0) {
                        values.money_cost.push(queryData.money_cost);
                        values.execution_time.push(queryData.execution_time);

                        // Get quality metric
                        const qualityMetric = getQualityMetric(queryData);
                        if (qualityMetric !== null) {
                            values.quality.push(qualityMetric);
                        }
                    }
                }
            });
            
            // Calculate statistics if we have data
            if (values.money_cost.length > 0) {
                aggregatedData[system][query] = {
                    status: 'success',
                    money_cost: calculateMean(values.money_cost),
                    money_cost_std: calculateStd(values.money_cost),
                    execution_time: calculateMean(values.execution_time),
                    execution_time_std: calculateStd(values.execution_time),
                    quality_mean: values.quality.length > 0 ? calculateMean(values.quality) : null,
                    quality_std: values.quality.length > 0 ? calculateStd(values.quality) : null,
                    round_count: values.money_cost.length,
                    hasMultipleRounds: values.money_cost.length > 1
                };
                
                // Add backward compatibility fields (match Python logic)
                const qualityMean = aggregatedData[system][query].quality_mean;
                if (qualityMean !== null) {
                    // Add accuracy field like Python does (line 465 in table_brick_design.py)
                    aggregatedData[system][query].accuracy = qualityMean;

                    // Also add f1_score for backward compatibility with getQualityMetric
                    if (values.quality.length > 0) {
                        aggregatedData[system][query].f1_score = qualityMean;
                    }
                }
            }
        });
    });
    
    return aggregatedData;
}

function calculateMean(values) {
    if (values.length === 0) return null;
    return values.reduce((sum, val) => sum + val, 0) / values.length;
}

function calculateStd(values) {
    if (values.length <= 1) return 0;
    const mean = calculateMean(values);
    // Use population std (divide by N, not N-1) to match Python's np.std() default behavior
    const variance = values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length;
    return Math.sqrt(variance);
}

async function getAvailableSystems() {
    // This function is no longer used with the new round-based loading
    // but keeping it for backward compatibility
    const possibleSystems = ['bigquery', 'lotus', 'palimpzest', 'thalamusdb', 'snowflake'];
    return possibleSystems;
}

function populateTable() {
    const tbody = $('#tableBody');
    tbody.empty();
    
    // Update table title
    const scenarioName = currentScenario === 'mmqa' ? 'MMQA' :
                         currentScenario === 'ecomm' ? 'E-commerce' :
                         currentScenario.charAt(0).toUpperCase() + currentScenario.slice(1);
    const modelName = scenarioData[currentScenario].modelNames[currentModel];
    $('#tableTitle').html(`
        ${scenarioName} Scenario - ${modelName}
        <br>
        <span id="tracesHint">
            <i>Click on query names in the first column (e.g., Q1) to see detailed results and implementation</i>
        </span>
    `);
    
    // Get available systems and sort them in desired order
    const systemOrder = ['lotus', 'palimpzest', 'thalamusdb', 'bigquery', 'snowflake'];
    const availableSystems = Object.keys(systemsData).sort((a, b) => {
        const indexA = systemOrder.indexOf(a);
        const indexB = systemOrder.indexOf(b);
        // If both systems are in the order array, sort by their position
        if (indexA !== -1 && indexB !== -1) {
            return indexA - indexB;
        }
        // If only one is in the order array, prioritize it
        if (indexA !== -1) return -1;
        if (indexB !== -1) return 1;
        // If neither is in the order array, fall back to alphabetical
        return a.localeCompare(b);
    });
    
    // Populate system headers (systems as columns)
    populateSystemHeaders(availableSystems);
    
    // Create rows for each query (use custom queries if available, otherwise Q1-Q10)
    const queries = scenarioData[currentScenario].queries ||
                   Array.from({length: 10}, (_, i) => `Q${i + 1}`);

    queries.forEach(queryId => {
        const row = createQueryRow(queryId, availableSystems);
        tbody.append(row);
    });
    
    // Add summary rows
    const avgRow = createSummaryRow('Avg', availableSystems, 'average');
    const stdRow = createSummaryRow('Std Dev', availableSystems, 'stddev');
    tbody.append(avgRow);
    tbody.append(stdRow);
}

function populateSystemHeaders(availableSystems) {
    const systemHeaderRow = $('#systemHeaderRow');
    const metricHeaderRow = $('#metricHeaderRow');
    
    // Clear existing headers (keep first column)
    systemHeaderRow.find('th').slice(1).remove();
    metricHeaderRow.find('th').slice(1).remove();
    
    // Add system headers with 3 columns each
    availableSystems.forEach(system => {
        const systemName = formatSystemName(system);
        systemHeaderRow.append(`<th colspan="3" class="system-header"><strong>${systemName}</strong></th>`);
    });
    
    // Add metric sub-headers
    availableSystems.forEach(system => {
        metricHeaderRow.append('<th class="metric-header">Cost</th>');
        metricHeaderRow.append('<th class="metric-header">Quality</th>');
        metricHeaderRow.append('<th class="metric-header">Latency</th>');
    });
}

function createQueryRow(queryId, availableSystems) {
    const row = $('<tr>');
    
    // First column: Query ID with modalities and operators
    const queryCell = createQueryInfoCell(queryId);
    row.append(queryCell);
    
    // Collect all metric values for this query to calculate min/max for color coding
    const allCosts = [];
    const allQualities = [];
    const allLatencies = [];
    
    availableSystems.forEach(system => {
        const queryData = systemsData[system] && systemsData[system][queryId];
        if (queryData && queryData.status === 'success') {
            if (queryData.money_cost) allCosts.push(queryData.money_cost);
            
            const qualityMetric = getQualityMetric(queryData);
            if (qualityMetric !== null) allQualities.push(qualityMetric);
            
            if (queryData.execution_time) allLatencies.push(queryData.execution_time);
        }
    });
    
    // Calculate min/max for normalization
    const costRange = { min: Math.min(...allCosts), max: Math.max(...allCosts) };
    const qualityRange = { min: Math.min(...allQualities), max: Math.max(...allQualities) };
    const latencyRange = { min: Math.min(...allLatencies), max: Math.max(...allLatencies) };
    
    // Add cells for each system (3 columns per system)
    availableSystems.forEach(system => {
        const queryData = systemsData[system] && systemsData[system][queryId];
        
        if (queryData && queryData.status === 'success') {
            const qualityMetric = getQualityMetric(queryData);
            const hasMultipleRounds = queryData.hasMultipleRounds || false;

            // Cost cell with color coding (lower is better - green to red)
            const costText = formatCostCompact(queryData.money_cost, queryData.money_cost_std, hasMultipleRounds);
            const costColorClass = getCostColorClass(queryData.money_cost, costRange);
            row.append(`<td class="metric-cell cost-cell ${costColorClass}">${costText}</td>`);

            // Quality cell with color coding (higher is better - red to green)
            const qualityMean = queryData.quality_mean || qualityMetric;
            const qualityText = formatQualityCompact(qualityMean, queryData.quality_std, hasMultipleRounds);
            const qualityColorClass = qualityMean !== null ? getQualityColorClass(qualityMean, qualityRange) : '';
            row.append(`<td class="metric-cell quality-cell ${qualityColorClass}">${qualityText}</td>`);

            // Latency cell with color coding (lower is better - green to red)
            const latencyText = formatLatencyCompact(queryData.execution_time, queryData.execution_time_std, hasMultipleRounds);
            const latencyColorClass = queryData.execution_time ? getLatencyColorClass(queryData.execution_time, latencyRange) : '';
            row.append(`<td class="metric-cell latency-cell ${latencyColorClass}">${latencyText}</td>`);
        } else {
            // No data available for this system/query
            row.append('<td class="metric-cell">N/A</td>');
            row.append('<td class="metric-cell">N/A</td>');
            row.append('<td class="metric-cell">N/A</td>');
        }
    });
    
    return row;
}

function createQueryInfoCell(queryId) {
    let cellContent = `
        <div class="query-main">
            <a href="#" class="query-link" data-query="${queryId}">${queryId}</a>
        </div>`;
    
    // Add modalities and operators if coverage data is available
    if (coverageData && coverageData.queries) {
        const queryCoverage = coverageData.queries.find(q => q.id === queryId);
        if (queryCoverage) {
            cellContent += '<div class="query-indicators">';
            
            // Add modality badges (filter out 'table' modality)
            if (queryCoverage.modalities && queryCoverage.modalities.length > 0) {
                const filteredModalities = queryCoverage.modalities.filter(modality => modality !== 'table');
                if (filteredModalities.length > 0) {
                    cellContent += '<div class="modality-badges">';
                    filteredModalities.forEach(modality => {
                        cellContent += `<span class="modality-badge ${modality}">${modality.charAt(0).toUpperCase()}</span>`;
                    });
                    cellContent += '</div>';
                }
            }
            
            // Add operator badges
            if (queryCoverage.operators && queryCoverage.operators.length > 0) {
                cellContent += '<div class="operator-badges">';
                queryCoverage.operators.forEach(operator => {
                    cellContent += `<span class="operator-badge ${operator}">${operator.charAt(0).toUpperCase()}</span>`;
                });
                cellContent += '</div>';
            }
            
            cellContent += '</div>';
        }
    }
    
    return `<td class="query-name-cell">${cellContent}</td>`;
}

function getCostColorClass(cost, range) {
    if (range.max === range.min) {
        // Single value case - use absolute thresholds
        // Cost thresholds: < $0.01 = excellent, < $0.10 = good, >= $0.10 = poor
        const baseClass = cost < 0.01 ? 'performance-excellent' :
                         cost < 0.10 ? 'performance-good' : 'performance-poor';
        return colorblindMode ? `${baseClass}-cb` : baseClass;
    }
    const normalized = (cost - range.min) / (range.max - range.min);

    // For cost, lower is better: 0 (min cost) = excellent, 1 (max cost) = poor
    const baseClass = normalized <= 0.33 ? 'performance-excellent' :
                     normalized <= 0.66 ? 'performance-good' : 'performance-poor';

    return colorblindMode ? `${baseClass}-cb` : baseClass;
}

function getQualityColorClass(quality, range) {
    // Use absolute quality thresholds instead of relative comparison
    // Quality metrics are typically 0-1 scale where higher is better
    const baseClass = quality >= 0.8 ? 'performance-excellent' :  // >= 80%
                     quality >= 0.6 ? 'performance-good' :        // >= 60%
                     'performance-poor';                           // < 60%

    return colorblindMode ? `${baseClass}-cb` : baseClass;
}

function getLatencyColorClass(latency, range) {
    if (range.max === range.min) {
        // Single value case - use absolute thresholds
        // Latency thresholds: < 5s = excellent, < 30s = good, >= 30s = poor
        const baseClass = latency < 5 ? 'performance-excellent' :
                         latency < 30 ? 'performance-good' : 'performance-poor';
        return colorblindMode ? `${baseClass}-cb` : baseClass;
    }
    const normalized = (latency - range.min) / (range.max - range.min);

    // For latency, lower is better: 0 (min latency) = excellent, 1 (max latency) = poor
    const baseClass = normalized <= 0.33 ? 'performance-excellent' :
                     normalized <= 0.66 ? 'performance-good' : 'performance-poor';

    return colorblindMode ? `${baseClass}-cb` : baseClass;
}

function createSummaryRow(label, availableSystems, summaryType) {
    const row = $('<tr class="summary-row">');
    
    // First column: Summary label
    row.append(`<td class="summary-label"><strong>${label}</strong></td>`);
    
    // Calculate and add summary metrics for each system
    availableSystems.forEach(system => {
        const systemData = systemsData[system];
        
        if (systemData) {
            const summaryMetrics = calculateSystemSummary(systemData, summaryType);
            
            // Cost summary
            row.append(`<td class="metric-cell summary-cell">${summaryMetrics.cost}</td>`);
            
            // Quality summary
            row.append(`<td class="metric-cell summary-cell">${summaryMetrics.quality}</td>`);
            
            // Latency summary
            row.append(`<td class="metric-cell summary-cell">${summaryMetrics.latency}</td>`);
        } else {
            row.append('<td class="metric-cell summary-cell">--</td>');
            row.append('<td class="metric-cell summary-cell">--</td>');
            row.append('<td class="metric-cell summary-cell">--</td>');
        }
    });
    
    return row;
}

function calculateSystemSummary(systemData, summaryType) {
    const costs = [];
    const qualities = [];
    const latencies = [];
    const costVars = [];
    const qualityVars = [];
    const latencyVars = [];
    
    // Collect values from all queries (use custom queries if available, otherwise Q1-Q10)
    const queries = scenarioData[currentScenario].queries ||
                   Array.from({length: 10}, (_, i) => `Q${i + 1}`);

    queries.forEach(queryId => {
        const queryData = systemData[queryId];

        // Match Python logic: only check if query exists and has data (no status check)
        if (queryData) {
            // For average calculation - Python doesn't require > 0
            if ('money_cost' in queryData && queryData.money_cost !== null) {
                costs.push(queryData.money_cost);
            }

            if ('accuracy' in queryData && queryData.accuracy !== null) {
                qualities.push(queryData.accuracy);
            }

            if ('execution_time' in queryData && queryData.execution_time !== null) {
                latencies.push(queryData.execution_time);
            }

            // For std dev calculation - match Python's exact logic
            if (summaryType === 'stddev') {
                // Cost relative variance - check: not null AND not undefined AND > 0
                const cost = queryData.money_cost;
                const cost_std = queryData.money_cost_std;
                if (cost !== null && cost !== undefined &&
                    cost_std !== null && cost_std !== undefined &&
                    cost > 0) {
                    costVars.push(cost_std / cost);
                }

                // Quality relative variance - use "accuracy" like Python, not getQualityMetric
                const quality = queryData.accuracy;
                const quality_std = queryData.quality_std;
                if (quality !== null && quality !== undefined &&
                    quality_std !== null && quality_std !== undefined &&
                    quality > 0) {
                    qualityVars.push(quality_std / quality);
                }

                // Latency relative variance
                const latency = queryData.execution_time;
                const latency_std = queryData.execution_time_std;
                if (latency !== null && latency !== undefined &&
                    latency_std !== null && latency_std !== undefined &&
                    latency > 0) {
                    latencyVars.push(latency_std / latency);
                }
            }
        }
    });

    if (summaryType === 'average') {
        return {
            cost: costs.length > 0 ? formatCost(calculateMean(costs)) : '--',
            quality: qualities.length > 0 ? calculateMean(qualities).toFixed(2) : '--',
            latency: latencies.length > 0 ? 
                (calculateMean(latencies) >= 1 ? 
                    `${calculateMean(latencies).toFixed(1)}s` : 
                    `${calculateMean(latencies).toFixed(2)}s`) : '--'
        };
    } else if (summaryType === 'stddev') {
        // Return relative variance as percentages
        return {
            cost: costVars.length > 0 ? `±${(calculateMean(costVars) * 100).toFixed(1)}%` : '--',
            quality: qualityVars.length > 0 ? `±${(calculateMean(qualityVars) * 100).toFixed(1)}%` : '--',
            latency: latencyVars.length > 0 ? `±${(calculateMean(latencyVars) * 100).toFixed(1)}%` : '--'
        };
    }
}

// Old createTableRow function removed - replaced with createQueryRow

function formatSystemName(systemName) {
    const nameMap = {
        'lotus': 'LOTUS',
        'palimpzest': 'Palimpzest',
        'thalamusdb': 'ThalamusDB',
        'bigquery': 'BigQuery',
        'snowflake': 'Snowflake'
    };

    const displayName = nameMap[systemName] || systemName;

    // Add version number if available
    if (systemVersions && systemVersions[displayName]) {
        return `${displayName} (${systemVersions[displayName]})`;
    }

    return displayName;
}

function calculateOverallMetrics(systemData) {
    let totalQuality = 0;
    let totalCost = 0;
    let queryCount = 0;
    let validQualityCount = 0;
    let qualityValues = [];
    let costValues = [];
    let hasAggregatedData = false;
    
    Object.keys(systemData).forEach(queryKey => {
        if (queryKey.startsWith('Q')) {
            const queryData = systemData[queryKey];
            if (queryData.status === 'success') {
                // Check if this is aggregated data
                if (queryData.hasMultipleRounds) {
                    hasAggregatedData = true;
                }
                
                const qualityMetric = getQualityMetric(queryData);
                if (qualityMetric !== null) {
                    totalQuality += qualityMetric;
                    validQualityCount++;
                    qualityValues.push(qualityMetric);
                }
                totalCost += queryData.money_cost;
                costValues.push(queryData.money_cost);
                queryCount++;
            }
        }
    });
    
    const result = {
        quality: validQualityCount > 0 ? totalQuality / validQualityCount : null,
        cost: totalCost
    };
    
    // Calculate standard deviations if we have aggregated data
    if (hasAggregatedData) {
        result.qualityStd = qualityValues.length > 1 ? calculateStd(qualityValues) : 0;
        result.costStd = costValues.length > 1 ? calculateStd(costValues) : 0;
    }
    
    return result;
}

function getQualityMetric(queryData) {
    // Transform metrics to 0-1 scale where larger is better, following the Python logic

    // Check for pre-computed mean quality (from aggregated rounds)
    if (queryData.quality_mean !== undefined && queryData.quality_mean !== null) {
        return queryData.quality_mean;
    }

    // Check for specific metric types
    if (queryData.f1_score !== undefined && queryData.f1_score !== null) {
        return queryData.f1_score;
    } else if (queryData.metric_type === 'adjusted-rand-index' && queryData.accuracy !== undefined && queryData.accuracy !== null) {
        // For adjusted rand index, the value is stored in the accuracy field
        return queryData.accuracy;
    } else if (queryData.relative_error !== undefined) {
        const rel_err = queryData.relative_error;
        return rel_err !== null ? 1 / (1 + rel_err) : null;
    } else if (queryData.spearman_correlation !== undefined && queryData.spearman_correlation !== null) {
        return queryData.spearman_correlation;
    } else if (queryData.accuracy !== undefined && queryData.accuracy !== null) {
        // Generic accuracy metric (used by some queries when metric_type is not specified)
        return queryData.accuracy;
    } else if (queryData.precision !== undefined && queryData.precision !== null) {
        return queryData.precision;
    } else if (queryData.recall !== undefined && queryData.recall !== null) {
        return queryData.recall;
    }
    return null;
}

async function loadCoverageData() {
    try {
        const dataPath = `${getDataBasePath()}/${currentScenario}/query/coverage.json`;
        const response = await fetch(dataPath);
        if (response.ok) {
            const data = await response.json();
            console.log(`Loaded coverage data for ${currentScenario}:`, data);
            return data;
        }
    } catch (error) {
        console.log(`No coverage data found for ${currentScenario}, using default table view`);
    }
    return null;
}

async function loadSystemVersions() {
    try {
        const versionPath = `${getDataBasePath()}/system_version.json`;
        const response = await fetch(versionPath);
        if (response.ok) {
            const data = await response.json();
            console.log('Loaded system versions:', data);
            return data;
        }
    } catch (error) {
        console.log('No system version data found, using system names without versions');
    }
    return {};
}

function getPerformanceClass(qualityMetric) {
    if (qualityMetric >= 0.8) return 'high-performance';
    if (qualityMetric >= 0.5) return 'medium-performance';
    return 'low-performance';
}

function onQueryClick(event) {
    event.preventDefault();
    const queryId = $(event.target).attr('data-query') || $(event.target).attr('id');
    console.log('Query clicked:', queryId);
    
    if (queryId && queryId.startsWith('Q')) {
        showQueryDetails(queryId);
    }
}

async function showQueryDetails(queryId) {
    try {
        console.log(`Loading details for query: ${queryId}`);
        
        // Load natural language query (try .json for MMQA, fallback to .txt)
        let naturalLanguage = 'Not available';
        try {
            if (currentScenario === 'mmqa') {
                const naturalLanguageJsonPath = `${getDataBasePath()}/${currentScenario}/query/natural_language/${queryId.toLowerCase()}.json`;
                const jsonResponse = await fetch(naturalLanguageJsonPath);
                if (jsonResponse.ok) {
                    const jsonData = await jsonResponse.json();
                    naturalLanguage = jsonData.nl_question || 'Not available';
                }
            } else {
                const naturalLanguagePath = `${getDataBasePath()}/${currentScenario}/query/natural_language/${queryId}.txt`;
                const naturalLanguageResponse = await fetch(naturalLanguagePath);
                naturalLanguage = naturalLanguageResponse.ok ? await naturalLanguageResponse.text() : 'Not available';
            }
        } catch (error) {
            console.warn('Error loading natural language query:', error);
        }

        // Load SQL implementation (try lowercase for MMQA)
        let sqlImplementation = 'Not available';
        try {
            const sqlPath = currentScenario === 'mmqa' ?
                `${getDataBasePath()}/${currentScenario}/query/bigquery/${queryId.toLowerCase()}.sql` :
                `${getDataBasePath()}/${currentScenario}/query/bigquery/${queryId}.sql`;
            const sqlResponse = await fetch(sqlPath);
            sqlImplementation = sqlResponse.ok ? await sqlResponse.text() : 'Not available';
        } catch (error) {
            console.warn('Error loading SQL implementation:', error);
        }
        
        // Create query details content
        const content = `
            <div class="query-content">
                <h3 class="title is-4">Query ${queryId.slice(1)} Details</h3>
                
                <div class="query-section">
                    <h4>Natural Language Question</h4>
                    <div class="query-text">${naturalLanguage}</div>
                </div>
                
                <div class="query-section">
                    <h4>BigQuery Implementation</h4>
                    <div class="query-sql" id="sqlContent"></div>
                </div>
                
                <div class="query-section">
                    <h4>Query Performance Comparison</h4>
                    <div class="query-image">
                        <img src="${getFiguresBasePath()}/${currentScenario}/${scenarioData[currentScenario].pathPrefix}${currentModel}/query_pareto/${queryId}.png"
                             alt="Query ${queryId} Performance Chart"
                             style="max-width: 600px; height: auto;"
                             onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                        <p style="display: none; color: #666; font-style: italic;">Performance chart not available</p>
                    </div>
                </div>
                
                <div class="query-section">
                    <h4>System Performance Summary</h4>
                    <div class="systems-summary">
                        ${createSystemsSummary(queryId)}
                    </div>
                </div>
            </div>
        `;
        
        $('#queryDetailsContent').html(content);
        // Set the SQL content with proper HTML rendering
        $('#sqlContent').html(highlightSQL(sqlImplementation));
        $('#queryDetails').show();
        
        // Scroll to query details
        $('#queryDetails')[0].scrollIntoView({ behavior: 'smooth' });
        
    } catch (error) {
        console.error('Error loading query details:', error);
        showError('Failed to load query details');
    }
}

function createSystemsSummary(queryId) {
    let summaryHtml = '<div class="systems-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem;">';
    
    Object.keys(systemsData).forEach(systemName => {
        const queryData = systemsData[systemName][queryId];
        if (queryData) {
            const qualityMetric = getQualityMetric(queryData);
            const performanceClass = getPerformanceClass(qualityMetric);
            const hasMultipleRounds = queryData.hasMultipleRounds || false;
            
            // Format values with error bars if applicable
            let qualityText, costText, timeText;
            if (hasMultipleRounds) {
                qualityText = formatQualityWithError(queryData.quality_mean || qualityMetric, queryData.quality_std, hasMultipleRounds);
                costText = formatCostWithError(queryData.money_cost, queryData.money_cost_std, hasMultipleRounds);
                timeText = formatTimeWithError(queryData.execution_time, queryData.execution_time_std, hasMultipleRounds);
            } else {
                qualityText = qualityMetric ? qualityMetric.toFixed(3) : 'N/A';
                costText = formatCost(queryData.money_cost);
                timeText = queryData.execution_time ? `${queryData.execution_time.toFixed(1)}s` : 'N/A';
            }
            
            summaryHtml += `
                <div class="system-summary ${performanceClass}">
                    <h5>${formatSystemName(systemName)}</h5>
                    <p><strong>Quality:</strong> ${qualityText}</p>
                    <p><strong>Cost:</strong> ${costText}</p>
                    <p><strong>Time:</strong> ${timeText}</p>
                    <p><strong>Status:</strong> ${queryData.status}</p>
                </div>
            `;
        }
    });
    
    summaryHtml += '</div>';
    return summaryHtml;
}

// Old populateQueryHeaders function removed - replaced with populateSystemHeaders

// Old createQueryHeader and createCoverageIndicators functions removed

function showPerformanceCharts() {
    const pathPrefix = scenarioData[currentScenario].pathPrefix;
    const content = `
        <div class="performance-chart">
            <h4>Pareto Frontier - Cost vs Quality</h4>
            <img src="${getFiguresBasePath()}/${currentScenario}/${pathPrefix}${currentModel}/${currentScenario}_${currentModel}_pareto.png"
                 alt="Pareto Chart"
                 style="max-width: 100%; height: auto;"
                 onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
            <p style="display: none; color: #666; font-style: italic;">Pareto chart not available</p>
        </div>

        <div class="performance-chart">
            <h4>Performance Metrics Overview</h4>
            <img src="${getFiguresBasePath()}/${currentScenario}/${pathPrefix}${currentModel}/${currentScenario}_${currentModel}_performance_error_bar.png"
                 alt="Performance Chart"
                 style="max-width: 100%; height: auto;"
                 onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
            <p style="display: none; color: #666; font-style: italic;">Performance chart not available</p>
        </div>
    `;

    $('#performanceCharts').html(content);
    $('#overallPerformance').show();
}

function showLoading() {
    $('#tableBody').html('<tr><td colspan="13" style="text-align: center;"><div class="loading"></div> Loading benchmark data...</td></tr>');
}

function hideLoading() {
    // Loading is hidden when table is populated
}

function showError(message) {
    $('#tableBody').html(`<tr><td colspan="13" class="error" style="text-align: center;">${message}</td></tr>`);
}

function formatCost(cost) {
    if (cost === 0 || cost === null || cost === undefined) {
        return '$0.00';
    }
    
    // Convert to scientific notation to count significant digits
    const costStr = cost.toString();
    
    if (cost >= 1) {
        // For costs >= $1, show 2 decimal places
        return '$' + cost.toFixed(2);
    }
    
    // For small costs, show first 2 non-zero digits
    if (cost < 1) {
        // Convert to string and find significant digits
        let significantDigits = costStr.replace(/^0*\.0*/, ''); // Remove leading zeros and decimal
        
        if (significantDigits.length === 0) {
            return '$0.00';
        }
        
        // Count decimal places needed to show 2 significant digits
        const leadingZeros = costStr.indexOf('.') !== -1 ? 
            costStr.substring(costStr.indexOf('.') + 1).match(/^0*/)[0].length : 0;
        
        const decimalPlaces = Math.min(leadingZeros + 2, 8); // Show 2 sig digits, max 8 decimals
        return '$' + cost.toFixed(decimalPlaces);
    }
    
    return '$' + cost.toFixed(2);
}

function formatCostWithError(meanCost, stdCost, hasMultipleRounds) {
    if (!hasMultipleRounds || stdCost === 0 || stdCost === null || stdCost === undefined) {
        return formatCost(meanCost);
    }
    
    const meanStr = formatCost(meanCost).replace('$', '');
    const stdStr = formatCost(stdCost).replace('$', '');
    return `$${meanStr} ± $${stdStr}`;
}

function formatQualityWithError(meanQuality, stdQuality, hasMultipleRounds) {
    if (meanQuality === null || meanQuality === undefined) {
        return 'N/A';
    }
    
    if (!hasMultipleRounds || stdQuality === 0 || stdQuality === null || stdQuality === undefined) {
        return meanQuality.toFixed(2);
    }
    
    return `${meanQuality.toFixed(2)} ± ${stdQuality.toFixed(2)}`;
}

function formatTimeWithError(meanTime, stdTime, hasMultipleRounds) {
    if (meanTime === null || meanTime === undefined) {
        return 'N/A';
    }

    const timeStr = meanTime >= 1 ? meanTime.toFixed(1) : meanTime.toFixed(2);

    if (!hasMultipleRounds || stdTime === 0 || stdTime === null || stdTime === undefined) {
        return `${timeStr}s`;
    }

    const stdStr = stdTime >= 1 ? stdTime.toFixed(1) : stdTime.toFixed(2);
    return `${timeStr}s ± ${stdStr}s`;
}

// Compact formatting functions for table cells with std dev on separate lines
function formatCostCompact(meanCost, stdCost, hasMultipleRounds) {
    if (meanCost === null || meanCost === undefined) {
        return 'N/A';
    }

    const mainValue = formatCost(meanCost);

    if (!hasMultipleRounds || stdCost === 0 || stdCost === null || stdCost === undefined) {
        return mainValue;
    }

    const stdValue = formatCost(stdCost).replace('$', '');
    return `${mainValue}<br><span class="std-dev">±${stdValue}</span>`;
}

function formatQualityCompact(meanQuality, stdQuality, hasMultipleRounds) {
    if (meanQuality === null || meanQuality === undefined) {
        return 'N/A';
    }

    const mainValue = meanQuality.toFixed(2);

    if (!hasMultipleRounds || stdQuality === 0 || stdQuality === null || stdQuality === undefined) {
        return mainValue;
    }

    return `${mainValue}<br><span class="std-dev">±${stdQuality.toFixed(2)}</span>`;
}

function formatLatencyCompact(meanLatency, stdLatency, hasMultipleRounds) {
    if (meanLatency === null || meanLatency === undefined) {
        return 'N/A';
    }

    const mainValue = meanLatency >= 1 ? `${meanLatency.toFixed(1)}s` : `${meanLatency.toFixed(2)}s`;

    if (!hasMultipleRounds || stdLatency === 0 || stdLatency === null || stdLatency === undefined) {
        return mainValue;
    }

    const stdValue = stdLatency >= 1 ? `${stdLatency.toFixed(1)}s` : `${stdLatency.toFixed(2)}s`;
    return `${mainValue}<br><span class="std-dev">±${stdValue}</span>`;
}

function highlightSQL(sql) {
    if (!sql || sql === 'Not available') {
        return sql;
    }
    
    // Simple approach: just apply highlighting without complex escaping
    let result = sql;
    
    // Keywords (case insensitive)
    result = result.replace(/\b(SELECT|FROM|WHERE|JOIN|INNER|LEFT|RIGHT|OUTER|ON|AS|AND|OR|NOT|IN|EXISTS|BETWEEN|LIKE|IS|NULL|ORDER|BY|GROUP|HAVING|LIMIT|OFFSET|UNION|DISTINCT|COUNT|SUM|AVG|MAX|MIN|CASE|WHEN|THEN|ELSE|END|INSERT|UPDATE|DELETE|CREATE|TABLE|INDEX|DROP|ALTER|DATABASE|SCHEMA|VIEW|PRIMARY|FOREIGN|KEY|REFERENCES|CASCADE|CHECK|DEFAULT|UNIQUE|AUTO_INCREMENT|TIMESTAMP|VARCHAR|INT|INTEGER|BIGINT|DECIMAL|FLOAT|DOUBLE|BOOLEAN|DATE|TIME|DATETIME|TEXT|BLOB|JSON|WITH|RECURSIVE|CTE|WINDOW|OVER|PARTITION|ROW_NUMBER|RANK|DENSE_RANK|LAG|LEAD|FIRST_VALUE|LAST_VALUE|NTILE)\b/gi, '<span class="sql-keyword">$1</span>');
    
    // Functions
    result = result.replace(/\b(AI\.IF|IF|COALESCE|ISNULL|CONCAT|SUBSTRING|LENGTH|UPPER|LOWER|TRIM|REPLACE|CAST|CONVERT|ROUND|CEIL|FLOOR|ABS|SQRT|POW|MOD|NOW|CURRENT_TIMESTAMP|CURRENT_DATE|CURRENT_TIME|YEAR|MONTH|DAY|HOUR|MINUTE|SECOND|DATEDIFF|DATEADD)\b/gi, '<span class="sql-function">$1</span>');
    
    // Strings with single quotes
    result = result.replace(/'([^']*)'/g, '<span class="sql-string">\'$1\'</span>');
    
    // Numbers
    result = result.replace(/\b(\d+\.?\d*)\b/g, '<span class="sql-number">$1</span>');
    
    // Comments
    result = result.replace(/(--.*$)/gm, '<span class="sql-comment">$1</span>');
    
    return result;
}