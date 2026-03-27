"""Submit multiple axs queries into SLURM queue and wait on their completion.

    NB: needs cython Python package installed and pyslurm Python package COMPILED using this cython before running this code.

Usage examples :
                    # see this cookbook:
                axs byname slurm , help

                    # submit one job only (default query)
                axs byname slurm , submit_one

                    # submit one job only (specific query)
                axs byname slurm , submit_one python_package,package_name=pillow

                    # submit all jobs (default queries)
                axs byname slurm , submit_all

                    # submit all jobs (specific queries)
                axs byname slurm , submit_all --:=python_package,package_name=numpy:python_package,package_name=pillow

                    # submit all jobs and poll their states until completion of all:
                axs byname slurm , babysit --refresh=5

                    # cleanup (CAREFUL, in case you had other python_package-s installed!)
                axs all_byquery python_package ---='[["remove"]]'
"""

import pyslurm
import time

def submit_one(query):

    desc = pyslurm.JobSubmitDescription(
        name=f"axs2slurm",
        partitions="krai",
        account="krai_users",
        comment="docker",
        time_limit="00:05:00",          # 5 minutes for now
        required_nodes="sith6,sith7",   # SLURM should pick one of the nodes
        ntasks=1,
        cpus_per_task=1,
        memory_per_node="500M",         # very light job
        script=f"#!/bin/bash\n\naxs byquery {query}",
    )

    job_id = None
    try:
        job_id = desc.submit()
        print(f"Submitted job_id={job_id} query={query}")
    except Exception as e:
        print(f"Failed to submit job {query}: {e}")

    return job_id


def submit_all(queries):

    jobid_2_query = {}
    for query in queries:
        job_id = submit_one(query)
        if job_id:
            jobid_2_query[job_id] = query

    return jobid_2_query


def babysit(jobid_2_query, refresh=3):

    print(f"Polling every {refresh} seconds until all jobs complete or fail...\n")

    completed_jobs = set()
    failed_states = {"FAILED", "CANCELLED", "TIMEOUT", "NODE_FAIL", "OUT_OF_MEMORY"}

    while len(completed_jobs) < len(jobid_2_query):
        current_jobs = pyslurm.job().get()

        still_active = 0
        for job_id in jobid_2_query:
            query = jobid_2_query[job_id]
            if job_id in completed_jobs:
                continue

            if job_id not in current_jobs:
                # Job no longer in queue → assume finished
                completed_jobs.add(job_id)
                print(f"  Job job_id={job_id}  query={query}  disappeared (likely finished)")
                continue

            state = current_jobs[job_id]["job_state"]
            if state in ("COMPLETED",) or state in failed_states:
                completed_jobs.add(job_id)
                print(f"  Job job_id={job_id}  query={query}  → {state}")
            else:
                still_active += 1

        if still_active > 0:
            print(f"  {still_active} jobs still running/pending...")
            time.sleep(refresh)
        else:
            break

    print("\nAll jobs have finished.")

