   select
       sales_line_id,
       days_in_stock,
       sales_amount,
       profit_amount
   from {{ ref('fact_sales') }}
   where days_in_stock < 0
      or sales_amount < 0