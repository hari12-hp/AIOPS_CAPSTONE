"""Local-mode Spark transformations. Does not collect the source dataset to the driver."""
import argparse, json, time
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("input"); parser.add_argument("--output",default="data/cleaned/records"); parser.add_argument("--report",default="reports/eda/quality.json"); parser.add_argument("--min-solution-chars",type=int,default=12); parser.add_argument("--max-solution-chars",type=int,default=12000); args=parser.parse_args(); started=time.monotonic()
    try: from pyspark.sql import SparkSession, functions as F
    except ImportError as exc: raise SystemExit("PySpark is required for this stage: " + str(exc))
    spark=SparkSession.builder.master("local[2]").appName("local-math-cleaning").config("spark.ui.enabled","false").getOrCreate()
    try:
        raw=spark.read.json(args.input); input_count=raw.count()
        df=raw.withColumn("problem",F.trim("problem")).withColumn("solution",F.trim("solution"))
        malformed=(F.col("problem").isNull() | (F.length("problem")==0) | F.col("solution").isNull() | (F.length("solution")<args.min_solution_chars) | (F.length("solution")>args.max_solution_chars))
        kept=df.where(~malformed).withColumn("normalised_problem",F.lower(F.regexp_replace("problem",r"\\s+"," ")))
        before_dedup=kept.count(); clean=kept.dropDuplicates(["normalised_problem","solution"]); output_count=clean.count(); clean.write.mode("overwrite").json(args.output)
        report={"input_count":input_count,"output_count":output_count,"rejected_malformed":input_count-before_dedup,"duplicates":before_dedup-output_count,"seconds":time.monotonic()-started,"records_per_second":output_count/max(time.monotonic()-started,0.001),"engine":"pyspark-local"}
    finally: spark.stop()
    Path(args.report).parent.mkdir(parents=True,exist_ok=True); Path(args.report).write_text(json.dumps(report,indent=2)+"\n")
if __name__=="__main__": main()
