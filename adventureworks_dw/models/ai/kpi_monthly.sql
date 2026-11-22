{{ config(materialized='table', schema='ai') }}
with monthly as (
    select datefromparts(d.[year], d.month_number, 1) as month_start,
           cast(sum(f.sales_amount) as decimal(19,2)) as sales_amount,
           cast(sum(f.profit_amount) as decimal(19,2)) as profit_amount,
           count(distinct f.order_number) as order_count,
           sum(f.order_quantity) as units_sold
    from {{ ref('fact_sales') }} f
    inner join {{ ref('dim_date') }} d on d.date_key=f.order_date_key
    group by datefromparts(d.[year], d.month_number, 1)
), changes as (
    select c.*, p.sales_amount as prior_month_sales,
           y.sales_amount as prior_year_sales
    from monthly c
    left join monthly p on p.month_start=dateadd(month,-1,c.month_start)
    left join monthly y on y.month_start=dateadd(year,-1,c.month_start)
)
select month_start, sales_amount, profit_amount, order_count, units_sold,
       cast(sales_amount / nullif(order_count,0) as decimal(19,2)) as aov,
       prior_month_sales, prior_year_sales,
       cast(100.0*(sales_amount-prior_month_sales)/nullif(prior_month_sales,0) as decimal(18,2)) as sales_mom_pct,
       cast(100.0*(sales_amount-prior_year_sales)/nullif(prior_year_sales,0) as decimal(18,2)) as sales_yoy_pct
from changes
