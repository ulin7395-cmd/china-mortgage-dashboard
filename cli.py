import click
import pandas as pd
from datetime import datetime
from core.calculator import (
    calc_equal_installment, 
    calc_equal_principal_first_month,
    generate_schedule,
    generate_combined_schedule,
    calc_irr,
    calc_remaining_irr
)
from data_manager.excel_handler import (
    get_all_plans,
    get_plan_by_id,
    save_plan,
    delete_plan,
    get_rate_adjustments,
    save_rate_adjustment,
    get_prepayments,
    save_prepayment,
    update_prepayment,
    get_all_config,
    get_config,
    set_config
)
from core.schedule_generator import get_plan_schedule
from core.comparison import compare_plans, compare_repayment_methods

@click.group()
def cli():
    """A CLI for the loan dashboard project."""
    pass

@cli.command()
@click.option('--principal', type=float, required=True, help='Loan principal')
@click.option('--annual-rate', type=float, required=True, help='Annual interest rate')
@click.option('--term-months', type=int, required=True, help='Loan term in months')
def equal_installment(principal, annual_rate, term_months):
    """Calculates the monthly payment and total interest for an equal installment loan."""
    monthly_payment, total_interest = calc_equal_installment(principal, annual_rate, term_months)
    click.echo(f"Monthly payment: {monthly_payment:.2f}")
    click.echo(f"Total interest: {total_interest:.2f}")

@cli.command()
@click.option('--principal', type=float, required=True, help='Loan principal')
@click.option('--annual-rate', type=float, required=True, help='Annual interest rate')
@click.option('--term-months', type=int, required=True, help='Loan term in months')
def equal_principal(principal, annual_rate, term_months):
    """Calculates the first month payment and total interest for an equal principal loan."""
    first_month_payment, total_interest = calc_equal_principal_first_month(principal, annual_rate, term_months)
    click.echo(f"First month payment: {first_month_payment:.2f}")
    click.echo(f"Total interest: {total_interest:.2f}")

@cli.command('generate-schedule')
@click.option('--plan-id', type=str, required=True, help='Plan ID')
@click.option('--principal', type=float, required=True, help='Loan principal')
@click.option('--annual-rate', type=float, required=True, help='Annual interest rate')
@click.option('--term-months', type=int, required=True, help='Loan term in months')
@click.option('--repayment-method', type=click.Choice(['equal_installment', 'equal_principal']), required=True, help='Repayment method')
@click.option('--start-date', type=str, required=True, help='Start date (YYYY-MM-DD)')
@click.option('--repayment-day', type=int, default=1, help='Repayment day')
def generate_schedule_command(plan_id, principal, annual_rate, term_months, repayment_method, start_date, repayment_day):
    """Generates a repayment schedule and outputs it as CSV."""
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
    schedule = generate_schedule(plan_id, principal, annual_rate, term_months, repayment_method, start_date_obj, repayment_day)
    click.echo(schedule.to_csv(index=False))

@cli.command('generate-combined-schedule')
@click.option('--plan-id', type=str, required=True, help='Plan ID')
@click.option('--commercial-amount', type=float, required=True, help='Commercial loan amount')
@click.option('--provident-amount', type=float, required=True, help='Provident fund loan amount')
@click.option('--commercial-rate', type=float, required=True, help='Commercial loan annual rate')
@click.option('--provident-rate', type=float, required=True, help='Provident fund loan annual rate')
@click.option('--term-months', type=int, required=True, help='Loan term in months')
@click.option('--repayment-method', type=click.Choice(['equal_installment', 'equal_principal']), required=True, help='Repayment method')
@click.option('--start-date', type=str, required=True, help='Start date (YYYY-MM-DD)')
@click.option('--repayment-day', type=int, default=1, help='Repayment day')
def generate_combined_schedule_command(plan_id, commercial_amount, provident_amount, commercial_rate, provident_rate, term_months, repayment_method, start_date, repayment_day):
    """Generates a combined loan repayment schedule and outputs it as CSV."""
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
    schedule = generate_combined_schedule(plan_id, commercial_amount, provident_amount, commercial_rate, provident_rate, term_months, repayment_method, start_date_obj, repayment_day)
    click.echo(schedule.to_csv(index=False))

@cli.command('calc-irr')
@click.option('--principal', type=float, required=True, help='Loan principal')
@click.option('--schedule-file', type=click.Path(exists=True), required=True, help='Path to the repayment schedule CSV file')
def calc_irr_command(principal, schedule_file):
    """Calculates the IRR for a loan."""
    schedule = pd.read_csv(schedule_file)
    irr = calc_irr(principal, schedule)
    click.echo(f"IRR: {irr:.4f}%")

@cli.command('calc-remaining-irr')
@click.option('--remaining-principal', type=float, required=True, help='Remaining loan principal')
@click.option('--schedule-file', type=click.Path(exists=True), required=True, help='Path to the remaining repayment schedule CSV file')
def calc_remaining_irr_command(remaining_principal, schedule_file):
    """Calculates the IRR for the remaining part of a loan."""
    schedule = pd.read_csv(schedule_file)
    irr = calc_remaining_irr(remaining_principal, schedule)
    click.echo(f"Remaining IRR: {irr:.4f}%")

@cli.command('list-plans')
def list_plans():
    """Lists all loan plans."""
    plans = get_all_plans()
    click.echo(plans.to_string())

@cli.command('get-plan')
@click.option('--plan-id', type=str, required=True, help='Plan ID')
def get_plan(plan_id):
    """Gets a loan plan by its ID."""
    plan = get_plan_by_id(plan_id)
    if plan is not None:
        click.echo(plan.to_string())
    else:
        click.echo(f"Plan with ID '{plan_id}' not found.")

@cli.command('add-plan')
@click.option('--plan-id', type=str, required=True, help='Plan ID')
@click.option('--plan-name', type=str, required=True, help='Plan name')
@click.option('--loan-type', type=click.Choice(['commercial', 'provident', 'combined']), required=True, help='Loan type')
@click.option('--total-amount', type=float, required=True, help='Total loan amount')
@click.option('--commercial-amount', type=float, help='Commercial loan amount')
@click.option('--provident-amount', type=float, help='Provident fund loan amount')
@click.option('--term-months', type=int, required=True, help='Loan term in months')
@click.option('--repayment-method', type=click.Choice(['equal_installment', 'equal_principal']), required=True, help='Repayment method')
@click.option('--commercial-rate', type=float, help='Commercial loan annual rate')
@click.option('--provident-rate', type=float, help='Provident fund loan annual rate')
@click.option('--start-date', type=str, required=True, help='Start date (YYYY-MM-DD)')
@click.option('--repayment-day', type=int, default=1, help='Repayment day')
@click.option('--status', type=click.Choice(['active', 'completed', 'archived']), default='active', help='Plan status')
@click.option('--notes', type=str, help='Notes')
def add_plan(plan_id, plan_name, loan_type, total_amount, commercial_amount, provident_amount, term_months, repayment_method, commercial_rate, provident_rate, start_date, repayment_day, status, notes):
    """Adds a new loan plan."""
    plan_dict = {
        'plan_id': plan_id,
        'plan_name': plan_name,
        'loan_type': loan_type,
        'total_amount': total_amount,
        'commercial_amount': commercial_amount,
        'provident_amount': provident_amount,
        'term_months': term_months,
        'repayment_method': repayment_method,
        'commercial_rate': commercial_rate,
        'provident_rate': provident_rate,
        'start_date': start_date,
        'repayment_day': repayment_day,
        'status': status,
        'notes': notes
    }
    save_plan(plan_dict)
    click.echo(f"Plan with ID '{plan_id}' added successfully.")

@cli.command('delete-plan')
@click.option('--plan-id', type=str, required=True, help='Plan ID')
def delete_plan_command(plan_id):
    """Deletes a loan plan by its ID."""
    delete_plan(plan_id)
    click.echo(f"Plan with ID '{plan_id}' deleted successfully.")

@cli.command('list-rate-adjustments')
@click.option('--plan-id', type=str, required=True, help='Plan ID')
def list_rate_adjustments(plan_id):
    """Lists all rate adjustments for a plan."""
    adjustments = get_rate_adjustments(plan_id)
    click.echo(adjustments.to_string())

@cli.command('add-rate-adjustment')
@click.option('--adjustment-id', type=str, required=True, help='Adjustment ID')
@click.option('--plan-id', type=str, required=True, help='Plan ID')
@click.option('--effective-date', type=str, required=True, help='Effective date (YYYY-MM-DD)')
@click.option('--effective-period', type=int, required=True, help='Effective period')
@click.option('--rate-type', type=click.Choice(['commercial', 'provident']), required=True, help='Rate type')
@click.option('--old-rate', type=float, required=True, help='Old rate')
@click.option('--new-rate', type=float, required=True, help='New rate')
@click.option('--lpr-value', type=float, help='LPR value')
@click.option('--basis-points', type=int, help='Basis points')
@click.option('--reason', type=str, help='Reason')
def add_rate_adjustment(adjustment_id, plan_id, effective_date, effective_period, rate_type, old_rate, new_rate, lpr_value, basis_points, reason):
    """Adds a new rate adjustment."""
    adjustment_dict = {
        'adjustment_id': adjustment_id,
        'plan_id': plan_id,
        'effective_date': effective_date,
        'effective_period': effective_period,
        'rate_type': rate_type,
        'old_rate': old_rate,
        'new_rate': new_rate,
        'lpr_value': lpr_value,
        'basis_points': basis_points,
        'reason': reason
    }
    save_rate_adjustment(adjustment_dict)
    click.echo(f"Rate adjustment with ID '{adjustment_id}' added successfully.")

@cli.command('list-prepayments')
@click.option('--plan-id', type=str, required=True, help='Plan ID')
def list_prepayments(plan_id):
    """Lists all prepayments for a plan."""
    prepayments = get_prepayments(plan_id)
    click.echo(prepayments.to_string())

@cli.command('add-prepayment')
@click.option('--prepayment-id', type=str, required=True, help='Prepayment ID')
@click.option('--plan-id', type=str, required=True, help='Plan ID')
@click.option('--prepayment-date', type=str, required=True, help='Prepayment date (YYYY-MM-DD)')
@click.option('--prepayment-period', type=int, required=True, help='Prepayment period')
@click.option('--amount', type=float, required=True, help='Prepayment amount')
@click.option('--method', type=click.Choice(['shorten_term', 'reduce_payment']), required=True, help='Prepayment method')
def add_prepayment(prepayment_id, plan_id, prepayment_date, prepayment_period, amount, method):
    """Adds a new prepayment."""
    prepayment_dict = {
        'prepayment_id': prepayment_id,
        'plan_id': plan_id,
        'prepayment_date': prepayment_date,
        'prepayment_period': prepayment_period,
        'amount': amount,
        'method': method
    }
    save_prepayment(prepayment_dict)
    click.echo(f"Prepayment with ID '{prepayment_id}' added successfully.")

@cli.command('update-prepayment')
@click.option('--prepayment-id', type=str, required=True, help='Prepayment ID')
@click.option('--updates', type=str, required=True, help='Updates in JSON format')
def update_prepayment_command(prepayment_id, updates):
    """Updates a prepayment."""
    import json
    updates_dict = json.loads(updates)
    update_prepayment(prepayment_id, updates_dict)
    click.echo(f"Prepayment with ID '{prepayment_id}' updated successfully.")

@cli.command('list-configs')
def list_configs():
    """Lists all system configurations."""
    configs = get_all_config()
    click.echo(configs.to_string())

@cli.command('get-config')
@click.option('--key', type=str, required=True, help='Config key')
def get_config_command(key):
    """Gets a system configuration by its key."""
    value = get_config(key)
    if value is not None:
        click.echo(value)
    else:
        click.echo(f"Config with key '{key}' not found.")

@cli.command('set-config')
@click.option('--key', type=str, required=True, help='Config key')
@click.option('--value', type=str, required=True, help='Config value')
@click.option('--description', type=str, help='Description')
def set_config_command(key, value, description):
    """Sets a system configuration."""
    set_config(key, value, description)
    click.echo(f"Config with key '{key}' set successfully.")

@cli.command('compare-plans')
@click.argument('plan_ids', nargs=-1)
def compare_plans_command(plan_ids):
    """Compares multiple loan plans."""
    if len(plan_ids) < 2:
        click.echo("Please provide at least two plan IDs to compare.")
        return

    all_plans = get_all_plans()
    selected_plans = all_plans[all_plans["plan_id"].isin(plan_ids)]
    plan_list = selected_plans.to_dict("records")

    schedules = {}
    for p in plan_list:
        sch = get_plan_schedule(p["plan_id"])
        if not sch.empty:
            for col in ["monthly_payment", "principal", "interest", "remaining_principal",
                        "cumulative_principal", "cumulative_interest"]:
                sch[col] = pd.to_numeric(sch[col], errors="coerce").fillna(0)
            schedules[p["plan_id"]] = sch

    comp_df = compare_plans(plan_list, schedules)
    if not comp_df.empty:
        click.echo("--- Key Metrics Comparison ---")
        click.echo(comp_df.to_string())

@cli.command('compare-methods')
@click.option('--amount', type=float, required=True, help='Loan amount')
@click.option('--rate', type=float, required=True, help='Annual interest rate')
@click.option('--years', type=int, required=True, help='Loan term in years')
def compare_methods_command(amount, rate, years):
    """Compares equal installment and equal principal methods."""
    result = compare_repayment_methods(
        amount, rate, years * 12, datetime.today().date(),
    )
    click.echo("--- Equal Installment ---")
    click.echo(result["equal_installment"])
    click.echo("\n--- Equal Principal ---")
    click.echo(result["equal_principal"])
    click.echo(f"\nInterest difference: {result['利息差额']:.2f}")

if __name__ == "__main__":
    cli()
