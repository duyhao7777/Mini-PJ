   with source as (

       select * from {{ source('stg', 'sales') }}

   ),

   typed as (

       select
           try_convert(date, orderdate, 103) as order_date,
           try_convert(date, stockdate, 103) as stock_date,
           trim(ordernumber)                 as order_number,
           cast(productkey as int)           as product_key,
           cast(customerkey as int)          as customer_key,
           cast(territorykey as int)         as territory_key,
           cast(orderlineitem as int)        as order_line_item,
           cast(orderquantity as int)        as order_quantity,
           _batch_id                         as batch_id,
           _source_file                      as source_file,
           _loaded_at                        as loaded_at
       from source

   ),

   deduped as (

       select
           *,
           row_number() over (
               partition by order_number, order_line_item
               order by loaded_at desc
           ) as rn
       from typed

   )

   select
       order_date,
       stock_date,
       order_number,
       product_key,
       customer_key,
       territory_key,
       order_line_item,
       order_quantity,
       batch_id,
       source_file,
       loaded_at
   from deduped
   where rn = 1