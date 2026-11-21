   select
       row_number() over (order by return_date, territory_key, product_key) as return_id,
       cast(format(return_date, 'yyyyMMdd') as int)                         as return_date_key,
       product_key,
       territory_key,
       return_quantity
   from {{ ref('stg_returns') }}