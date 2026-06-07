-- Migration 021: Convert antikvaari_price.antikvaari_product_binding from free-text
-- to a FK reference to bindingtype (1=Ei tietoa/muu, 2=Nidottu, 3=Sidottu).

ALTER TABLE suomisf.antikvaari_price
    ALTER COLUMN antikvaari_product_binding TYPE INTEGER
    USING CASE
        WHEN antikvaari_product_binding ILIKE '%sidottu%' THEN 3
        WHEN antikvaari_product_binding ILIKE '%nidottu%'
          OR antikvaari_product_binding ILIKE '%pokkari%' THEN 2
        WHEN antikvaari_product_binding IS NOT NULL
          AND antikvaari_product_binding <> '' THEN 1
        ELSE NULL
    END;

ALTER TABLE suomisf.antikvaari_price
    ADD CONSTRAINT fk_antikvaari_price_binding
    FOREIGN KEY (antikvaari_product_binding)
    REFERENCES suomisf.bindingtype(id);
