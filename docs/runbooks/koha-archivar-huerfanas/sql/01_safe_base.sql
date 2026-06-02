SELECT b.borrowernumber, b.cardnumber, b.categorycode, b.userid,
       b.surname, b.firstname, b.email,
       DATE_FORMAT(b.dateexpiry,'%Y-%m-%d') AS dateexpiry,
       DATE_FORMAT(b.lastseen,'%Y-%m-%d') AS lastseen,
       (SELECT ba.attribute FROM borrower_attributes ba WHERE ba.borrowernumber=b.borrowernumber AND ba.code='DNI' LIMIT 1) AS attr_dni
FROM borrowers b
JOIN categories c USING(categorycode)
WHERE b.categorycode IN ('ESTUDI','ALUMNI','VISITA','DOCEN','ADMINIST','INVESTI','POSGRADO','JUBILADO','ADMIN')
  AND c.category_type <> 'S'
  AND (b.flags IS NULL OR b.flags = 0)
  AND b.protected = 0
  AND NOT EXISTS (SELECT 1 FROM issues i        WHERE i.borrowernumber=b.borrowernumber)
  AND NOT EXISTS (SELECT 1 FROM old_issues oi   WHERE oi.borrowernumber=b.borrowernumber)
  AND NOT EXISTS (SELECT 1 FROM reserves r      WHERE r.borrowernumber=b.borrowernumber)
  AND NOT EXISTS (SELECT 1 FROM old_reserves o2 WHERE o2.borrowernumber=b.borrowernumber)
  AND NOT EXISTS (SELECT 1 FROM accountlines a  WHERE a.borrowernumber=b.borrowernumber)
  AND NOT EXISTS (SELECT 1 FROM borrower_debarments d WHERE d.borrowernumber=b.borrowernumber);
