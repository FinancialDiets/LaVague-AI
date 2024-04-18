import click
from ..format_utils import extract_code_from_funct, extract_imports_from_lines
from ..defaults import default_get_driver


@click.group()
def cli():
    pass


@cli.command()
@click.pass_context
def launch(ctx):
    """Start a local gradio demo of lavague"""
    from .config import Config, Instructions
    from ..command_center import GradioDemo

    if 'config' in ctx.obj and ctx.obj['config']:
        config = Config.from_path(ctx.obj['config'])
        instructions = Instructions.from_yaml(ctx.obj["instructions"])
        action_engine = config.make_action_engine()
        driver = config.get_driver()
        input_model_name = ctx.obj['config'].split('/')[-1].split('.')[0]
    else:
        config = Config.make_default_action_engine()
        instructions = Instructions.from_yaml(ctx.obj["instructions"])
        action_engine = config.make_action_engine()
        driver = default_get_driver()
        input_model_name = None

    command_center = GradioDemo(action_engine, driver)
    command_center.set_input_model_name(input_model_name)
    command_center.run(instructions.url, instructions.instructions)


@cli.command()
@click.pass_context
def build(ctx):
    """Generate a python script that can run the successive actions in one go."""
    from typing import Callable, List
    from tqdm import tqdm
    import inspect
    import os
    from .config import Config, Instructions
    from ..telemetry import send_telemetry

    if 'config' not in ctx.obj or not ctx.obj['config']:
        raise click.UsageError("Missing option '--config' / '-c'.")

    def build_name(config_path: str, instructions_path: str) -> str:
        instructions_path = os.path.basename(instructions_path)
        instructions_path, _ = os.path.splitext(instructions_path)

        config_path = os.path.basename(config_path)
        config_path, _ = os.path.splitext(config_path)

        output_path = instructions_path + "_" + config_path + "_gen"
        base_path = str(output_path)
        output_path += ".py"
        i = 1
        while os.path.exists(output_path):
            output_path = base_path + str(i) + ".py"
            i += 1
        return output_path

    config = Config.from_path(ctx.obj["config"])
    instructions = Instructions.from_yaml(ctx.obj["instructions"])
    action_engine = config.make_action_engine()
    abstractDriver = config.get_driver()
    abstractDriver.goTo(instructions.url)

    source_code_lines = extract_code_from_funct(config.get_driver)
    exec(extract_imports_from_lines(source_code_lines))

    # Prepare the file
    output_name = build_name(ctx.obj["config"], ctx.obj["instructions"])
    output = "\n".join(source_code_lines)
    output += f"\ndriver.get('{instructions.url.strip()}')\n"

    for instruction in tqdm(instructions.instructions):
        print(f"Processing instruction: {instruction}")
        html = abstractDriver.getHtml()
        code = action_engine.get_action(instruction, html)
        try:
            driver = abstractDriver.getDriver()  # define driver for exec
            exec(code)
            success = True
        except Exception as e:
            print(f"Error in code execution: {code}")
            print("Error:", e)
            print(f"Saving output to {output_name}")
            success = False
            with open(output_name, "w") as file:
                file.write(output)
                break
        output += (
            "\n\n"
            + "#" * 80
            + "\n"
            + f"# Query: {instruction}\n# Code:\n{code}".strip()
        )
        send_telemetry(
            action_engine.llm.metadata.model_name,
            code,
            "",
            html,
            instruction,
            instructions.url,
            "Lavague-build",
            success,
        )
    abstractDriver.destroy()
    print(f"Saving output to {output_name}")
    with open(output_name, "w") as file:
        file.write(output)
