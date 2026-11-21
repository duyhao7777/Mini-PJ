   select
       cast(productkey as int)                                    as product_key,
       try_cast(productsubcategorykey as int)                     as product_subcategory_key,
       trim(productsku)                                           as product_sku,
       trim(productname)                                          as product_name,
       trim(modelname)                                            as model_name,
       trim(productdescription)                                   as product_description,
       coalesce(nullif(trim(productcolor), ''), 'N/A')            as product_color,
       case
           when nullif(trim(productsize), '') is null
             or trim(productsize) = '0' then 'N/A'
           else trim(productsize)
       end                                                        as product_size,
       case
           when nullif(trim(productstyle), '') is null
             or trim(productstyle) = '0' then 'N/A'
           else trim(productstyle)
       end                                                        as product_style,
       try_cast(productcost as decimal(18, 4))                    as product_cost,
       try_cast(productprice as decimal(18, 4))                   as product_price
   from {{ source('stg', 'product') }}