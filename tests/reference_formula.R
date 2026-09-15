# Independent evaluation of BioAge orig=TRUE, without the Python implementation.
# https://github.com/dayoonkwon/BioAge/blob/master/R/phenoage_calc.R
# CRP here is mg/dL, before natural log.
d <- data.frame(albumin=c(4.2,3.7),creatinine=c(.9,1.2),glucose=c(95,130),
                crp=c(.1,.5),lymph=c(30,22),mcv=c(90,94),rdw=c(13,15),
                alp=c(65,95),wbc=c(6.5,8.5),age=c(50,70))
xb <- with(d, -19.90667 - .03359355*albumin*10 + .009506491*creatinine*88.4017 +
           .1953192*glucose*.0555 + .09536762*log(crp) - .01199984*lymph +
           .02676401*mcv + .3306156*rdw + .001868778*alp + .05542406*wbc + .08035356*age)
m <- 1-exp(-1.51714*exp(xb)/.007692696)
age <- log(-.0055305*log(1-m))/.090165 + 141.50225
stopifnot(max(abs(age-c(43.70363251372635,83.53337985334832))) < 1e-10)
print(age, digits=16)
