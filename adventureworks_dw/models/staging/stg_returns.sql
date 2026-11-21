   select
       try_convert(date, returndate, 103) as return_date,
       cast(territorykey as int)          as territory_key,
       cast(productkey as int)            as product_key,
       cast(returnquantity as int)        as return_quantity
   from {{ source('stg', 'returns_data') }}