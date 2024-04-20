from tqdm import tqdm
import torch
from datasets import Dataset
import itertools

from benchita.task import SquadV2Task


def build_inference_dataset(*, tokenizer, task, num_shots, system_style, chat_template, apply_chat_template_args, max_length):
    inference_inputs = []

    for elem in tqdm(task.build(num_shots=num_shots, system_style=system_style), total=len(task), desc="Building Dataset"):
        elem["prompt"] = chat_template(
            elem["messages"],
            **apply_chat_template_args
        )
        inference_inputs.append(elem)

    inference_ds = Dataset.from_list(inference_inputs)
    inference_ds = inference_ds.map(lambda x: tokenizer(x["prompt"], padding="max_length", truncation=False, max_length=max_length), batched=True)

    return inference_ds


def run_inference(*, dataset, model, tokenizer, task, batch_size, generate_args, device, dry_run):
    inference_outputs = []
    for i in tqdm(range(0, len(dataset), batch_size), total=len(dataset) // batch_size):
        batch = dataset[i:i+batch_size]
        input_ids = torch.tensor(batch["input_ids"], device=device)
        attention_mask = torch.tensor(batch["attention_mask"], device=device)

        with torch.no_grad():
            outputs = model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=task.max_new_tokens,
                pad_token_id=tokenizer.eos_token_id,
                **generate_args
            )

            outputs = tokenizer.batch_decode(outputs[:, input_ids.size(1):], skip_special_tokens=True)

            for messages, expected, prompt, output in zip(batch["messages"], batch["expected"], batch["prompt"], outputs):
                inference_outputs.append({
                    "messages": messages,
                    "expected": expected,
                    "input": prompt,
                    "output": output.strip()
                })

            if isinstance(task, SquadV2Task):
                for k, j in enumerate(range(i, i+batch_size)):
                    inference_outputs[j]['id'] = batch["id"][k]
                    inference_outputs[j]['answer_start'] = batch["answer_start"][k]

        if dry_run:
            break
    
    return inference_outputs


def build_jobs(config):
    jobs = []
    for task, model in itertools.product(config.tasks, config.models):
        jobs.append({
            "task": task,
            "model": model
        })
    return jobs