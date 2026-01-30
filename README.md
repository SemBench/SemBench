<table border="0">
  <tr>
    <td style="border: none;"><h1>SemBench: Benchmarking Semantic Query Processing Engines</h1></td>
    <td style="border: none;"><img src="assets/SemBench_logo.png" alt="SemBench Logo" width="1500"></td>
  </tr>
</table> 

SemBench is a benchmark targeting a novel class of systems: **semantic query processing engines**. Those systems rely inherently on generative and reasoning  capabilities of state-of-the-art large language models (LLMs). They extend SQL with semantic operators, configured by natural language instructions, that are evaluated via LLMs and enable users to perform various operations on multimodal data.

SemBench introduces diversity across three key dimensions: **scenarios, modalities, and operators**. Included are scenarios ranging from movie review analysis to car damage detection. Within these scenarios, we cover different data modalities, including images, audio, text, and table. Finally, the queries involve a diverse set of operators, including semantic filters, joins, mappings, ranking, and classification operators. 

Currently SemBench is evalulated on **three academic systems (LOTUS, Palimpzest, and ThalamusDB) and one industrial system, Google BigQuery**. Although these results reflect a snapshot of systems under continuous development, our study offers crucial insights into their current strengths and weaknesses, illuminating promising directions for future research.

We understand that every system is under rapid development, which is why we maintain an [online leaderboard](https://sembench.ngrok.io/). We encourage you to submit your system's results and participate in the benchmark. Please reach out to discuss how to contribute your results to the leaderboard.

## To Users: SemBench — A Simple, Ready-to-Use Benchmark

We understand that downloading datasets, generating databases, and setting up environments can be tedious—especially in the systems area, where each system often requires a unique setup. SemBench automates all of these steps for you! It automatically downloads datasets and generates multi-modal databases. Setting up environments for SemBench and four supported systems (LOTUS, Palimpzest, ThalamusDB, and BigQuery) takes just one script.

So, enjoy using SemBench! We believe a good benchmark should minimize user effort—and SemBench is designed exactly for that.

## Materials
- [Online Leaderboard](https://sembench.ngrok.io/)
- [Multi-Modal Datasets](https://drive.google.com/drive/folders/1pqf8DKFai16MR80Z7pcls5FgBbom-IJt?usp=sharing)
- [Paper](https://arxiv.org/abs/2511.01716)

## 🌟 Overview

Modern data systems increasingly need to process and reason over multi-modal data - combining traditional relational data with images, audio, and text. SemBench provides a standardized evaluation framework with:

- **5 Real-world Scenarios**: wildlife monitoring, car damage diagnosis, sentiment analysis of movie reviews, multi-modal question anwering, E-commerce product analysis
- **Multi-modal Queries**: Complex semantic operations across multi-modal databases: table, text, image, and audio  
- **System-agnostic Design**: Extensible and already supports LOTUS, Palimpzest, ThalamusDB, CAESURA, BigQuery, DuckDB FlockMTL
- **Comprehensive Metrics**: Quality (precision/recall/F1, relative error...), cost (money, token consumption), efficiency evaluation (execution time), and memory usage
- **Rich Visualizations**: Automated generation of performance comparisons

| Scenario | #Queries | Mod: Table | Mod: Text | Mod: Image | Mod: Audio | Op: Filter | Op: Join | Op: Map | Op: Rank | Op: Classify | Size: Text | Size: Image | Size: Audio |
| :--- | ---: | :---: | :---: | :---: | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Movie | 10 | ✓ | ✓ | -- | -- | 4 | 3 | -- | 2 | 1 | 1,375,738 | -- | -- |
| Wildlife | 10 | ✓ | -- | ✓ | ✓ | 17 | -- | -- | -- | -- | -- | 8,718 | 650 |
| E-Commerce | 14 | ✓ | ✓ | ✓ | -- | 12 | 9 | 3 | 1 | 2 | 44,446 | 44,446 | -- |
| MMQA | 11 | ✓ | ✓ | ✓ | -- | 5 | 3 | 4 | -- | -- | 5,000 | 1,000 | -- |
| Cars | 10 | ✓ | ✓ | ✓ | ✓ | 12 | -- | -- | -- | 1 | 157,376 | 30,131 | 1,387 |
| **Total** | **55** | **✓** | **✓** | **✓** | **✓** | **50** | **15** | **7** | **3** | **4** | **1,582,560** | **84295** | **2037** |

## 📁 Architecture

```
SemBench/
├── files/              # Use case data and queries
│   ├── {use_case}/
│   │   ├── data/           # Multi-modal datasets
│   │   ├── query/          # Natural language & SQL queries  
│   │   ├── metrics/        # System performance results
│   │   └── raw_results/    # Query execution outputs
├── figures/            # Performance visualizations  
├── src/                # Core implementation
│   ├── runner/            # System-specific implementations
│   ├── scenario/          # Use case logic & evaluation
│   ├── evaluator/         # Quality assessment framework
│   └── run.py            # Main benchmark orchestrator
└── README.md
```

## 🚀 Supported Scenarios

### 1. **Animals** - Wildlife Monitoring
*Data Modalities: Tables, Images, Audio*

Studies animal species detection and co-occurrence using camera traps and audio recorders. Features queries about species identification, location-based analysis, and cross-modal correlation between visual and audio evidence.

**Key Features**: Image-based species recognition, audio call classification, spatial-temporal analysis
**Queries**: 10 queries ranging from simple counts to complex multi-way joins
→ *[Detailed documentation](src/scenario/animals/README.md)*

### 2. **Cars** - Multi-Modal Car Damage Detection
*Data Modalities: Tables, Text, Images, Audio*  

In this scenario, the task is to diagnose whether a car has issues based on text, images, and audio recordings. A car may have zero, one, or multiple issues, and the multi-modal inputs may indicate either damage or a normal condition.

**Key Features**: Car damage detection from multiple modalities
**Queries**: 10 queries focusing on diagnostic accuracy and patient profiling
→ *[Detailed documentation](src/scenario/cars/README.md)*

### 3. **Movie** - Sentiment Analysis
*Data Modalities: Tables, Text*

Movie review sentiment analysis testing systems' understanding of emotional tone in textual content. Includes sentiment classification, comparison, and aggregation operations.

**Key Features**: Sentiment classification, review comparison, positivity ratio calculation  
**Queries**: 10 queries spanning filtering, joins, and aggregation operations
→ *[Detailed documentation](src/scenario/movie/README.md)*

### 4. **MMQA** - Multi-Modal Question Answering
*Data Modalities: Tables, Text, Images*

Based on the standard MultiModalQA dataset, testing question-answering capabilities across combined textual and visual information sources.

**Key Features**: Cross-modal question answering, information synthesis, knowledge reasoning

### 5. **Product** - Multi-Modal Amazon Fashion Product Analysis
*Data Modalities: Tables, Text, Images*

Based on the amazon fashion product dataset, making analysis over multi-modal product information

**Key Features**: Cross-modal product information analysis

## 🔧 System Support

SemBench supports evaluation of multiple multi-modal data systems:

- **LOTUS**: Semantic operators optimized by reducing costs with guaranteed accuracy
- **Palimpzest**: Semantic operators using cost-based optimization
- **ThalamusDB**: Semantic operators optimized with approximate query processing
- **CAESURA**: LLM-Based Multi-Modal Query Planner
- **FlockMTL**: An open-source extension of DuckDB   
- **BigQuery**: Google's analytics data warehouse

Each system implements a standardized runner interface enabling fair comparison across different architectural approaches. Also SemBench can be easily extended to support more systems.

## ⚡ Quick Start

### Large Language Model Provider Setup
Please refer to the `.env.example` file and create a corresponding `.env` file to configure the necessary credentials or API keys for using Gemini, OpenAI, or models provided by other platforms.
For the list of supported models for each system, please consult the corresponding repository for detailed information.

### Automatic Environment Setup
```bash
bash scripts/setup_environment.sh
```

### Automatic Dataset Download and Database Generation
Note

- SemBench automatically downloads the required datasets from Google Drive and constructs multi-modal databases according to the specified scale factor.

- The databases included in the repository are provided for demonstration purposes only. Before running your own experiments, please delete the existing `files/{scenario}/data` directory and execute the scripts to regenerate the data.

### Running Benchmarks
```bash
# Run specific system on specific use case and queries
python3 src/run.py --systems lotus --use-cases movie --queries 1 3 --model gemini-2.5-flash --scale-factor 2000

# Run full evaluation on a use case  
python3 src/run.py --systems lotus --use-cases movie --model gemini-2.5-flash --scale-factor 2000

# Compare multiple systems
python3 src/run.py --systems lotus thalamusdb --use-cases movie --model gemini-2.5-flash --scale-factor 2000

# Execute repeated experiments for error bars
# Please configure the script file first
cd scripts
./repeat_experiment.sh

# Generate performance visualizations
python3 src/plot.py

# Generate the latex table used in our paper
python3 src/table_brick_design.py

# Generate analysis report
python3 src/scripts/analysis.py
```

### Output Structure
Results are organized as:
- **Query Results**: `files/{scenario}/raw_results/{system}/Q{n}.csv`
- **Performance Metrics**: `files/{scenario}/metrics/{system}.json`  
- **Visualizations**: `figures/{scenario}/`

SemBench provides bar charts for every performance metric (money cost, latency, and result quality), pareto figure for cost-quality trade-off, and a comprehensive table in latex to compare all metrics.


## 🏗️ Extending the Benchmark

The modular architecture supports easy extension:

1. **Add New Use Cases**: Implement scenario-specific runner and evaluator
2. **Support New Systems**: Create system-specific runner inheriting from `GenericRunner`  
3. **Custom Metrics**: Extend evaluation framework with domain-specific quality measures
4. **Additional Queries**: Add query definitions in natural language and SQL formats


## 🤝 Contributing

We welcome contributions for new scenarios, systems, metrics, and more semantic queries! 

## Citation
If you use this benchmark, or otherwise found our work valuable, please cite 📒:
```
@misc{lao2025sembenchbenchmarksemanticquery,
      title={SemBench: A Benchmark for Semantic Query Processing Engines}, 
      author={Jiale Lao and Andreas Zimmerer and Olga Ovcharenko and Tianji Cong and Matthew Russo and Gerardo Vitagliano and Michael Cochez and Fatma Özcan and Gautam Gupta and Thibaud Hottelier and H. V. Jagadish and Kris Kissel and Sebastian Schelter and Andreas Kipf and Immanuel Trummer},
      year={2025},
      eprint={2511.01716},
      archivePrefix={arXiv},
      primaryClass={cs.DB},
      url={https://arxiv.org/abs/2511.01716}, 
}
```

---

*SemBench enables systematic evaluation of multi-modal data systems across diverse, realistic scenarios. Built for researchers and practitioners working at the intersection of databases, AI, and multi-modal data processing.*
